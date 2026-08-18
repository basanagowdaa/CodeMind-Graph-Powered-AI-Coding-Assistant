# demo-repository/__init__.py
"""
Demo repository — a realistic Python web application for CodeMind analysis.

Dependency chain (for the "BEFORE YOU CHANGE IT" demo):
  POST /login
       ↓ calls
  AuthService.authenticate_user()
       ↓ calls
  UserService.get_user_by_username() ──→ database.get_user_by_username() ──→ PostgreSQL
  UserService.verify_password()
  TokenService.create_access_token()
  TokenService.create_refresh_token() ──→ database.save_token() ──→ PostgreSQL
       ↓ tested by
  test_auth.py::TestAuthenticateUser
"""
