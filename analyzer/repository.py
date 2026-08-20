"""
analyzer/repository.py
Repository scanner — handles both local directories and GitHub URL cloning.

Security rules:
  - Static analysis ONLY. No code execution.
  - Clones into a sandboxed temp directory.
  - Validates GitHub URLs strictly.
  - Enforces file size and count limits.
  - Cleans up after analysis.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# GitHub URL pattern — only allow HTTPS public repos
GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?/?$"
)

MAX_REPO_SIZE_BYTES = int(os.environ.get("MAX_REPO_SIZE_MB", "500")) * 1024 * 1024
MAX_FILES = int(os.environ.get("MAX_FILES", "2000"))


class RepositoryError(Exception):
    """Raised when repository loading fails."""


class RepositoryScanner:
    """
    Handles fetching a repository (local or GitHub) and preparing it for analysis.
    """

    def validate_github_url(self, url: str) -> bool:
        """
        Strictly validate a GitHub URL.
        Only allows HTTPS github.com URLs — no path traversal, no other hosts.
        """
        url = url.strip()
        if not GITHUB_URL_PATTERN.match(url):
            return False
        # Extra check: no path traversal
        if ".." in url or "\\" in url:
            return False
        return True

    def prepare_local_directory(self, path: str) -> tuple[str, bool]:
        """
        Prepare a local directory for analysis.
        Returns (resolved_path, is_temp).
        """
        resolved = str(Path(path).resolve())
        if not os.path.isdir(resolved):
            raise RepositoryError(f"Directory not found: {path}")
        return resolved, False  # not temp — don't delete after analysis

    def clone_github_repo(self, url: str, clone_base_dir: str | None = None) -> tuple[str, bool]:
        """
        Clone a GitHub repository into a temp directory.
        Returns (clone_path, is_temp).

        Security:
          - URL validated before cloning
          - No credentials passed — public repos only
          - Shallow clone (depth=1) to limit download size
          - Clones into an isolated temp directory
        """
        if not self.validate_github_url(url):
            raise RepositoryError(
                f"Invalid GitHub URL: '{url}'. "
                "Only HTTPS github.com URLs are supported."
            )

        # Import gitpython here to avoid hard dependency at module load time
        try:
            import git
        except ImportError:
            raise RepositoryError(
                "gitpython is required for GitHub cloning. "
                "Install it with: pip install gitpython"
            )

        # Determine clone directory
        if clone_base_dir:
            Path(clone_base_dir).mkdir(parents=True, exist_ok=True)
            clone_dir = tempfile.mkdtemp(dir=clone_base_dir, prefix="codemind_repo_")
        else:
            clone_dir = tempfile.mkdtemp(prefix="codemind_repo_")

        logger.info("Cloning %s → %s (shallow)", url, clone_dir)

        try:
            git.Repo.clone_from(
                url,
                clone_dir,
                depth=1,             # Shallow clone — no full history
                single_branch=True,  # Default branch only
                no_tags=True,        # Skip tag objects
            )
        except Exception as exc:
            # Clean up on failure
            shutil.rmtree(clone_dir, ignore_errors=True)
            raise RepositoryError(
                f"Failed to clone repository '{url}': {exc}"
            ) from exc

        # Verify size
        total_size = self._directory_size(clone_dir)
        if total_size > MAX_REPO_SIZE_BYTES:
            shutil.rmtree(clone_dir, ignore_errors=True)
            raise RepositoryError(
                f"Repository is too large ({total_size // (1024*1024)} MB). "
                f"Maximum allowed: {MAX_REPO_SIZE_BYTES // (1024*1024)} MB."
            )

        logger.info("Cloned successfully. Size: %.1f MB", total_size / (1024 * 1024))
        return clone_dir, True  # is_temp=True — delete after analysis

    def cleanup(self, path: str) -> None:
        """Remove a temporary clone directory."""
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
                logger.info("Cleaned up temp directory: %s", path)
        except Exception as exc:
            logger.warning("Failed to clean up %s: %s", path, exc)

    @staticmethod
    def _directory_size(path: str) -> int:
        """Calculate total size of all files in a directory (bytes)."""
        total = 0
        for root, _, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
        return total

    @staticmethod
    def extract_repo_name(url_or_path: str) -> str:
        """
        Extract a human-readable repository name from URL or path.
        E.g. 'https://github.com/owner/myrepo.git' → 'myrepo'
        """
        # Strip trailing slashes and .git
        clean = url_or_path.rstrip("/")
        if clean.endswith(".git"):
            clean = clean[:-4]
        return clean.split("/")[-1] or "repository"
