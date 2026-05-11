import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any

import jwt
from flask import current_app, g, request, jsonify
from functools import wraps


SESSION_COOKIE_NAME = "session"


def _get_secret_key() -> str:
    secret = current_app.config.get("SECRET_KEY")
    if not secret:
        # Fallback for safety; Flask requires SECRET_KEY, but avoid crash
        secret = os.environ.get("SECRET_KEY", "dev")
    return secret


def _get_cookie_secure_flag() -> bool:
    # Gate Secure by environment: disable in debug/dev to allow HTTP localhost
    # Allow override via COOKIE_SECURE env var
    override = os.environ.get("COOKIE_SECURE")
    if override is not None:
        return override.lower() in ("1", "true", "yes", "on")
    return not bool(current_app.config.get("DEBUG", False))


def generate_session_token(user_id: int, email: str, expires_in_seconds: int = 900) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
    }
    token = jwt.encode(payload, _get_secret_key(), algorithm="HS256")
    # PyJWT returns str for PyJWT>=2
    return token


def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def set_session_cookie(response, token: str, max_age_seconds: int = 900):
    secure = _get_cookie_secure_flag()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age_seconds,
        httponly=True,
        secure=secure,
        samesite="Lax",
        path="/",
    )
    return response


def clear_session_cookie(response):
    secure = _get_cookie_secure_flag()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value="",
        max_age=0,
        httponly=True,
        secure=secure,
        samesite="Lax",
        path="/",
    )
    return response


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.cookies.get(SESSION_COOKIE_NAME)
        if not token:
            return jsonify({"message": "Authentication required"}), 401
        payload = verify_session_token(token)
        if not payload:
            return jsonify({"message": "Authentication required"}), 401
        # Attach to flask.g for downstream use
        g.current_user_id = int(payload.get("sub")) if payload.get("sub") is not None else None
        g.current_user_email = payload.get("email")
        if g.current_user_id is None:
            return jsonify({"message": "Authentication required"}), 401
        return fn(*args, **kwargs)
    return wrapper


