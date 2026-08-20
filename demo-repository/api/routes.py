"""
demo-repository/api/routes.py
FastAPI routes for the demo application.
Demonstrates API → Function relationships for the code graph.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Any

from ..services.auth_service import AuthService
from ..services.user_service import UserService


app = FastAPI(title="Demo App", description="Demo application for CodeMind analysis")

# Dependency injection
_auth_service = AuthService()
_user_service = UserService()


# ── Request / Response models ─────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Auth routes ───────────────────────────────────────────────────────────

@app.post("/login")
async def login(request: LoginRequest) -> dict[str, Any]:
    """
    POST /login — authenticate a user and issue tokens.
    Calls: AuthService.authenticate_user()
    """
    token_pair = _auth_service.authenticate_user(request.username, request.password)
    if token_pair is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return token_pair.to_dict()


@app.post("/logout")
async def logout(request: RefreshRequest) -> dict[str, Any]:
    """
    POST /logout — revoke a refresh token.
    Calls: AuthService.logout()
    """
    success = _auth_service.logout(request.refresh_token)
    return {"success": success}


@app.post("/refresh")
async def refresh_token(request: RefreshRequest) -> dict[str, Any]:
    """
    POST /refresh — exchange refresh token for a new token pair.
    Calls: AuthService.refresh_access_token()
    """
    pair = _auth_service.refresh_access_token(request.refresh_token)
    if pair is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    return pair.to_dict()


# ── User routes ───────────────────────────────────────────────────────────

@app.post("/register")
async def register(request: RegisterRequest) -> dict[str, Any]:
    """
    POST /register — create a new user account.
    Calls: UserService.create_user()
    """
    try:
        user = _user_service.create_user(
            request.username, request.email, request.password
        )
        return user.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/users/{user_id}")
async def get_user(
    user_id: str,
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    """
    GET /users/{user_id} — retrieve a user profile.
    Protected: requires Authorization header.
    Calls: AuthService.validate_token(), UserService.get_user()
    """
    token = authorization.removeprefix("Bearer ").strip()
    payload = _auth_service.validate_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = _user_service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


@app.get("/me")
async def get_current_user(authorization: str = Header(default="")) -> dict[str, Any]:
    """
    GET /me — get the currently authenticated user's profile.
    Calls: AuthService.validate_token(), UserService.get_user()
    """
    token = authorization.removeprefix("Bearer ").strip()
    payload = _auth_service.validate_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = _user_service.get_user(payload["sub"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()
