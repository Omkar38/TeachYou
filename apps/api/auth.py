from __future__ import annotations

from fastapi import Header, HTTPException, Query, Request

from apps.api.settings import settings


def require_auth(
    request: Request,
    token: str | None = Query(None),
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None),
) -> None:
    """Simple auth gate.

    - If API_AUTH_TOKEN is empty -> auth disabled.
    - Otherwise accept one of:
      * `Authorization: Bearer <token>`
      * `X-API-Key: <token>`
      * `?token=<token>` (needed for `<video>` and EventSource)
    """

    expected = (settings.api_auth_token or "").strip()
    if not expected:
        return

    if x_api_key and x_api_key.strip() == expected:
        return

    if token and token.strip() == expected:
        return

    if authorization:
        parts = authorization.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1] == expected:
            return

    raise HTTPException(status_code=401, detail="Unauthorized")
