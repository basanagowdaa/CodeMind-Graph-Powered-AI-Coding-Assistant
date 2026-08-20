"""
analyzer/parsers/python_parser.py
Python static analysis parser using the built-in `ast` module.

This module NEVER executes repository code.
It is a pure read-only static analysis tool.

Extracts:
  - Files (with module path)
  - Functions (name, params, return type, docstring, decorators, async)
  - Classes (name, base classes, methods)
  - Imports (from X import Y, import Z)
  - Function calls (caller → callee)
  - API endpoint definitions (FastAPI @app.get/post/put/delete/patch, Flask @app.route)
  - Test functions (prefixed with test_)
"""
from __future__ import annotations

import ast
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Data containers ────────────────────────────────────────────────────────

@dataclass
class ParsedFunction:
    name: str
    file: str
    line: int
    end_line: int
    parameters: list[str]
    return_annotation: str
    docstring: str
    source_code: str
    decorators: list[str]
    is_async: bool
    is_method: bool
    parent_class: str | None
    calls: list[str]     # names of functions/methods called
    is_test: bool

    # API-specific (derived from decorators)
    http_method: str = ""
    endpoint_path: str = ""


@dataclass
class ParsedClass:
    name: str
    file: str
    line: int
    end_line: int
    base_classes: list[str]
    methods: list[str]
    docstring: str
    source_code: str
    decorators: list[str]


@dataclass
class ParsedImport:
    file: str
    line: int
    module: str              # the imported module path
    symbols: list[str]       # specific names imported (empty = wildcard/module import)
    is_relative: bool
    level: int               # number of dots for relative imports (0 = absolute)


@dataclass
class ParsedFile:
    path: str                 # absolute path
    relative_path: str        # path relative to repo root
    module_path: str          # dotted module name (e.g. "services.auth_service")
    functions: list[ParsedFunction]
    classes: list[ParsedClass]
    imports: list[ParsedImport]
    source_code: str
    line_count: int
    has_errors: bool = False
    parse_error: str = ""


# ── Parser ─────────────────────────────────────────────────────────────────

class PythonParser:
    """
    Parses Python files using the standard ast module.
    Safe: performs no execution, no subprocess calls, no file writes.
    """

    # FastAPI route decorators we detect
    FASTAPI_ROUTE_DECORATORS = {
        "get", "post", "put", "delete", "patch", "options", "head",
        "websocket", "api_route",
    }
    # Flask route decorators
    FLASK_ROUTE_DECORATORS = {"route", "get", "post", "put", "delete", "patch"}

    def parse_file(self, file_path: str, repo_root: str) -> ParsedFile | None:
        """
        Parse a single Python file. Returns None if the file cannot be read.
        Never raises — errors are captured in ParsedFile.has_errors.
        """
        try:
            source = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError) as exc:
            logger.warning("Cannot read file %s: %s", file_path, exc)
            return None

        relative_path = os.path.relpath(file_path, repo_root).replace("\\", "/")
        module_path = self._path_to_module(relative_path)

        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as exc:
            logger.warning("Syntax error in %s: %s", file_path, exc)
            return ParsedFile(
                path=file_path,
                relative_path=relative_path,
                module_path=module_path,
                functions=[],
                classes=[],
                imports=[],
                source_code=source,
                line_count=source.count("\n") + 1,
                has_errors=True,
                parse_error=str(exc),
            )

        lines = source.splitlines()
        functions = self._extract_functions(tree, relative_path, lines, source)
        classes = self._extract_classes(tree, relative_path, lines, source)
        imports = self._extract_imports(tree, relative_path)

        return ParsedFile(
            path=file_path,
            relative_path=relative_path,
            module_path=module_path,
            functions=functions,
            classes=classes,
            imports=imports,
            source_code=source,
            line_count=len(lines),
        )

    # ── Function extraction ────────────────────────────────────────────────

    def _extract_functions(
        self,
        tree: ast.AST,
        file_path: str,
        lines: list[str],
        full_source: str,
    ) -> list[ParsedFunction]:
        """Extract all function and method definitions from the AST."""
        functions: list[ParsedFunction] = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Determine if this is a method (parent is a ClassDef)
            parent_class = self._get_parent_class(tree, node)

            # Parameters
            params = [arg.arg for arg in node.args.args]
            if params and params[0] in ("self", "cls"):
                params = params[1:]  # Strip self/cls for display

            # Return annotation
            return_ann = ""
            if node.returns:
                return_ann = ast.unparse(node.returns)

            # Docstring
            docstring = ast.get_docstring(node) or ""

            # Decorators
            decorators = [ast.unparse(d) for d in node.decorator_list]

            # Source code (extract lines)
            source_code = self._extract_source_lines(
                lines, node.lineno, getattr(node, "end_lineno", node.lineno)
            )

            # Function calls within this function
            calls = self._extract_calls(node)

            # API detection
            http_method, endpoint_path = self._detect_api_endpoint(
                node, decorators
            )

            # Is this a test function?
            is_test = (
                node.name.startswith("test_")
                or any("pytest" in d or "unittest" in d for d in decorators)
            )

            functions.append(ParsedFunction(
                name=node.name,
                file=file_path,
                line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                parameters=params,
                return_annotation=return_ann,
                docstring=docstring,
                source_code=source_code,
                decorators=decorators,
                is_async=isinstance(node, ast.AsyncFunctionDef),
                is_method=parent_class is not None,
                parent_class=parent_class,
                calls=calls,
                is_test=is_test,
                http_method=http_method,
                endpoint_path=endpoint_path,
            ))

        return functions

    def _extract_calls(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        """
        Extract all function/method call names within a function body.
        Returns simple names like 'get_user', 'validate_token'.
        """
        calls: list[str] = []
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node)
                if call_name:
                    calls.append(call_name)
        return list(dict.fromkeys(calls))  # deduplicate while preserving order

    def _get_call_name(self, call_node: ast.Call) -> str | None:
        """Extract a human-readable name from a Call node."""
        func = call_node.func
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            # e.g. self._users.get_user_by_username → get_user_by_username
            # or TokenService.create_access_token → create_access_token
            return func.attr
        return None

    # ── Class extraction ───────────────────────────────────────────────────

    def _extract_classes(
        self,
        tree: ast.AST,
        file_path: str,
        lines: list[str],
        full_source: str,
    ) -> list[ParsedClass]:
        """Extract all class definitions from the AST."""
        classes: list[ParsedClass] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            base_classes = []
            for base in node.bases:
                base_str = ast.unparse(base)
                # Simplify "services.auth_service.AuthService" → "AuthService"
                base_classes.append(base_str.rsplit(".", 1)[-1])

            methods = [
                n.name
                for n in ast.walk(node)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n is not node  # exclude the class node itself
            ]

            docstring = ast.get_docstring(node) or ""
            decorators = [ast.unparse(d) for d in node.decorator_list]
            source_code = self._extract_source_lines(
                lines, node.lineno, getattr(node, "end_lineno", node.lineno)
            )

            classes.append(ParsedClass(
                name=node.name,
                file=file_path,
                line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                base_classes=base_classes,
                methods=methods,
                docstring=docstring,
                source_code=source_code,
                decorators=decorators,
            ))

        return classes

    # ── Import extraction ──────────────────────────────────────────────────

    def _extract_imports(
        self, tree: ast.AST, file_path: str
    ) -> list[ParsedImport]:
        """Extract all import statements."""
        imports: list[ParsedImport] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(ParsedImport(
                        file=file_path,
                        line=node.lineno,
                        module=alias.name,
                        symbols=[],
                        is_relative=False,
                        level=0,
                    ))

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                symbols = [alias.name for alias in node.names]
                imports.append(ParsedImport(
                    file=file_path,
                    line=node.lineno,
                    module=module,
                    symbols=symbols,
                    is_relative=node.level > 0,
                    level=node.level,
                ))

        return imports

    # ── API endpoint detection ─────────────────────────────────────────────

    def _detect_api_endpoint(
        self,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        decorators: list[str],
    ) -> tuple[str, str]:
        """
        Detect FastAPI / Flask route decorators and extract HTTP method + path.
        Returns ("", "") if not an endpoint.
        """
        for dec in func_node.decorator_list:
            # Pattern: @app.get("/path"), @router.post("/path"), @app.route("/path")
            if isinstance(dec, ast.Call):
                func = dec.func
                if isinstance(func, ast.Attribute):
                    method_name = func.attr.upper()
                    # FastAPI-style: get, post, put, delete, patch
                    if func.attr.lower() in self.FASTAPI_ROUTE_DECORATORS:
                        path = self._extract_route_path(dec)
                        if path:
                            return method_name, path
                    # Flask route: @app.route("/path", methods=["POST"])
                    elif func.attr == "route":
                        path = self._extract_route_path(dec)
                        method = self._extract_flask_methods(dec)
                        if path:
                            return method or "GET", path
        return "", ""

    def _extract_route_path(self, call_node: ast.Call) -> str:
        """Extract the first string argument from a route decorator call."""
        if call_node.args:
            first_arg = call_node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                return first_arg.value
        return ""

    def _extract_flask_methods(self, call_node: ast.Call) -> str:
        """Extract methods=['POST'] from a Flask @app.route decorator."""
        for keyword in call_node.keywords:
            if keyword.arg == "methods" and isinstance(keyword.value, ast.List):
                for elt in keyword.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        return elt.value.upper()
        return "GET"

    # ── Helpers ────────────────────────────────────────────────────────────

    def _get_parent_class(
        self, tree: ast.AST, func_node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> str | None:
        """Find the class name that contains this function, if any."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in ast.walk(node):
                    if child is func_node:
                        return node.name
        return None

    def _extract_source_lines(
        self, lines: list[str], start: int, end: int
    ) -> str:
        """Extract source lines (1-indexed, inclusive)."""
        start_idx = max(0, start - 1)
        end_idx = min(len(lines), end)
        extracted = lines[start_idx:end_idx]
        # Limit to 50 lines for storage efficiency
        if len(extracted) > 50:
            extracted = extracted[:50] + ["    # ... (truncated)"]
        return "\n".join(extracted)

    @staticmethod
    def _path_to_module(relative_path: str) -> str:
        """Convert a relative file path to a dotted module name."""
        # Remove .py suffix
        if relative_path.endswith(".py"):
            relative_path = relative_path[:-3]
        # Replace path separators with dots
        module = relative_path.replace(os.sep, ".").replace("/", ".")
        # Remove __init__
        if module.endswith(".__init__"):
            module = module[: -len(".__init__")]
        return module
