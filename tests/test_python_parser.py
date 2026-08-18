"""
tests/test_python_parser.py
Unit tests for the Python AST parser.
These tests run WITHOUT HydraDB — pure static analysis tests.
"""
from __future__ import annotations

import os
import sys
import tempfile
import textwrap

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analyzer.parsers.python_parser import PythonParser


@pytest.fixture
def parser() -> PythonParser:
    return PythonParser()


@pytest.fixture
def tmp_dir(tmp_path) -> str:
    return str(tmp_path)


def write_py(tmp_path_str: str, filename: str, content: str) -> str:
    """Write a Python file and return its path."""
    path = os.path.join(tmp_path_str, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))
    return path


# ── Function extraction ────────────────────────────────────────────────────

class TestFunctionExtraction:

    def test_simple_function(self, parser, tmp_dir):
        path = write_py(tmp_dir, "sample.py", """
            def greet(name: str) -> str:
                '''Say hello.'''
                return f"Hello, {name}"
        """)
        result = parser.parse_file(path, tmp_dir)
        assert result is not None
        assert len(result.functions) == 1
        func = result.functions[0]
        assert func.name == "greet"
        assert func.parameters == ["name"]
        assert func.return_annotation == "str"
        assert "Say hello" in func.docstring
        assert func.is_async is False
        assert func.is_test is False

    def test_async_function(self, parser, tmp_dir):
        path = write_py(tmp_dir, "async_sample.py", """
            async def fetch_data(url: str):
                pass
        """)
        result = parser.parse_file(path, tmp_dir)
        assert result is not None
        func = next(f for f in result.functions if f.name == "fetch_data")
        assert func.is_async is True

    def test_method_in_class(self, parser, tmp_dir):
        path = write_py(tmp_dir, "cls_sample.py", """
            class MyService:
                def process(self, data: dict) -> bool:
                    return True
        """)
        result = parser.parse_file(path, tmp_dir)
        assert result is not None
        method = next(f for f in result.functions if f.name == "process")
        assert method.is_method is True
        assert method.parent_class == "MyService"
        assert "data" in method.parameters  # self is stripped

    def test_function_calls_extracted(self, parser, tmp_dir):
        path = write_py(tmp_dir, "calls_sample.py", """
            def authenticate_user(username, password):
                user = get_user_by_username(username)
                if verify_password(password, user.hashed_password):
                    return create_token(user.id)
                return None
        """)
        result = parser.parse_file(path, tmp_dir)
        assert result is not None
        func = next(f for f in result.functions if f.name == "authenticate_user")
        assert "get_user_by_username" in func.calls
        assert "verify_password" in func.calls
        assert "create_token" in func.calls


# ── Class extraction ───────────────────────────────────────────────────────

class TestClassExtraction:

    def test_simple_class(self, parser, tmp_dir):
        path = write_py(tmp_dir, "class_sample.py", """
            class TokenService:
                '''Handles JWT tokens.'''
                def create_token(self, user_id):
                    pass
                def validate_token(self, token):
                    pass
        """)
        result = parser.parse_file(path, tmp_dir)
        assert result is not None
        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "TokenService"
        assert "create_token" in cls.methods
        assert "validate_token" in cls.methods
        assert "Handles JWT tokens" in cls.docstring

    def test_class_with_inheritance(self, parser, tmp_dir):
        path = write_py(tmp_dir, "inherit_sample.py", """
            class AuthService(BaseService):
                pass
        """)
        result = parser.parse_file(path, tmp_dir)
        assert result is not None
        cls = result.classes[0]
        assert "BaseService" in cls.base_classes


# ── Import extraction ──────────────────────────────────────────────────────

class TestImportExtraction:

    def test_absolute_import(self, parser, tmp_dir):
        path = write_py(tmp_dir, "import_sample.py", """
            import os
            from pathlib import Path
        """)
        result = parser.parse_file(path, tmp_dir)
        assert result is not None
        modules = [i.module for i in result.imports]
        assert "os" in modules
        assert "pathlib" in modules

    def test_relative_import(self, parser, tmp_dir):
        path = write_py(tmp_dir, "rel_import.py", """
            from .auth_service import AuthService
            from ..database import get_db
        """)
        result = parser.parse_file(path, tmp_dir)
        assert result is not None
        rel_imports = [i for i in result.imports if i.is_relative]
        assert len(rel_imports) == 2
        assert any(i.level == 1 for i in rel_imports)
        assert any(i.level == 2 for i in rel_imports)


# ── Test function detection ────────────────────────────────────────────────

class TestTestDetection:

    def test_pytest_function_detected(self, parser, tmp_dir):
        path = write_py(tmp_dir, "test_auth.py", """
            def test_authenticate_user():
                result = authenticate_user("alice", "password")
                assert result is not None

            def test_validate_token():
                token = "abc"
                result = validate_token(token)
                assert result is None
        """)
        result = parser.parse_file(path, tmp_dir)
        assert result is not None
        test_funcs = [f for f in result.functions if f.is_test]
        assert len(test_funcs) == 2
        names = [f.name for f in test_funcs]
        assert "test_authenticate_user" in names
        assert "test_validate_token" in names


# ── API endpoint detection ─────────────────────────────────────────────────

class TestAPIEndpointDetection:

    def test_fastapi_post_endpoint(self, parser, tmp_dir):
        path = write_py(tmp_dir, "routes.py", """
            from fastapi import FastAPI
            app = FastAPI()

            @app.post("/login")
            async def login(request):
                pass

            @app.get("/users/{user_id}")
            async def get_user(user_id: str):
                pass
        """)
        result = parser.parse_file(path, tmp_dir)
        assert result is not None
        api_funcs = [f for f in result.functions if f.http_method]
        assert len(api_funcs) >= 2
        methods = {f.endpoint_path: f.http_method for f in api_funcs}
        assert "/login" in methods
        assert methods["/login"] == "POST"
        assert "/users/{user_id}" in methods
        assert methods["/users/{user_id}"] == "GET"


# ── Error handling ─────────────────────────────────────────────────────────

class TestErrorHandling:

    def test_syntax_error_handled_gracefully(self, parser, tmp_dir):
        path = write_py(tmp_dir, "broken.py", """
            def incomplete_function(
        """)
        result = parser.parse_file(path, tmp_dir)
        assert result is not None
        assert result.has_errors is True
        assert result.parse_error != ""

    def test_missing_file_returns_none(self, parser, tmp_dir):
        result = parser.parse_file("/nonexistent/path/file.py", tmp_dir)
        assert result is None
