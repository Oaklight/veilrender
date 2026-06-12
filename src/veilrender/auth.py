"""Token-based authentication."""

from __future__ import annotations

from veilrender._vendor.httpserver import HTTPException, Request
from veilrender.config import settings


def verify_token(request: Request) -> None:
    """Verify the API token from header or query param.

    Checks ``Authorization: Bearer <token>`` header first, then falls
    back to ``?token=<token>`` query parameter.

    Raises:
        HTTPException: 401 if token is invalid, 403 if token is missing.

    If ``VEILRENDER_API_TOKEN`` is not configured, auth is disabled.
    """
    expected = settings.api_token
    if expected is None:
        return

    # Check Authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token == expected:
            return
        raise HTTPException(401, "Invalid token")

    # Check query param
    token_params = request.query_params.get("token", [])
    if token_params:
        if token_params[0] == expected:
            return
        raise HTTPException(401, "Invalid token")

    raise HTTPException(403, "Authentication required")
