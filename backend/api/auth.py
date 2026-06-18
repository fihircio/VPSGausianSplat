from fastapi import Depends, Header, HTTPException, status, WebSocket
from sqlalchemy.orm import Session

from backend.services.auth_service import AuthContext, AuthService
from backend.utils.config import Settings, get_settings
from backend.utils.db import get_db

SCOPE_QUERY = "query"
SCOPE_WRITE = "write"
SCOPE_DELETE = "delete"


async def validate_auth(
    authorization: str | None = Header(None, alias="Authorization"),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> AuthContext:
    if settings.api_key is not None and x_api_key is not None and x_api_key.strip() == settings.api_key.strip():
        return AuthContext(tenant_id="admin", scopes=[SCOPE_QUERY, SCOPE_WRITE, SCOPE_DELETE], token_type="api_key")

    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
        ctx = AuthService.decode_access_token(token)
        if ctx is not None:
            return ctx

    if x_api_key:
        ctx = AuthService.verify_raw_api_key(x_api_key.strip(), db)
        if ctx is not None:
            return ctx

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid JWT or X-API-Key required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_scope(scope: str):
    async def _check(ctx: AuthContext = Depends(validate_auth)) -> AuthContext:
        if scope not in ctx.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{scope}' required",
            )
        return ctx
    return _check


async def validate_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.api_key is not None:
        if not x_api_key or x_api_key.strip() != settings.api_key.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-API-Key header",
            )


async def validate_ws_api_key(websocket: WebSocket, api_key: str | None = None) -> AuthContext:
    settings = get_settings()
    if settings.api_key is not None:
        if api_key and api_key.strip() == settings.api_key.strip():
            return AuthContext(tenant_id="admin", scopes=[SCOPE_QUERY, SCOPE_WRITE, SCOPE_DELETE], token_type="api_key")
    if api_key:
        from backend.utils.db import SessionLocal
        with SessionLocal() as db:
            ctx = AuthService.verify_raw_api_key(api_key.strip(), db)
            if ctx is not None:
                return ctx
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing api_key")
