import os
import secrets
from typing import Callable

from flask import request, jsonify, current_app


CSRF_COOKIE_NAME = "csrf_token"


def _get_cookie_secure_flag() -> bool:
    override = os.environ.get("COOKIE_SECURE")
    if override is not None:
        return override.lower() in ("1", "true", "yes", "on")
    return not bool(current_app.config.get("DEBUG", False))


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response, token: str | None = None):
    secure = _get_cookie_secure_flag()
    value = token or generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=value,
        max_age=60 * 60 * 24,  # 1 day
        httponly=False,  # must be readable by JS to send in header
        secure=secure,
        samesite="Lax",
        path="/",
    )
    return response


def clear_csrf_cookie(response):
    secure = _get_cookie_secure_flag()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value="",
        max_age=0,
        httponly=False,
        secure=secure,
        samesite="Lax",
        path="/",
    )
    return response


def csrf_protect(fn: Callable):
    """Decorator that enforces double-submit CSRF when a session cookie is present.

    - Only applies to state-changing methods.
    - If no session cookie is present, skip (e.g., login/register flows).
    """
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            # Only enforce if session cookie exists (authenticated context)
            if request.cookies.get("session"):
                header_token = request.headers.get("X-CSRF-Token")
                cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
                if not header_token or not cookie_token or header_token != cookie_token:
                    return jsonify({"message": "CSRF token invalid or missing"}), 403
        return fn(*args, **kwargs)

    return wrapper


