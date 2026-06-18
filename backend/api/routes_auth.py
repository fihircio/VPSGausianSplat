import logging

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from backend.api.schemas import RegisterRequest, RegisterResponse, TokenRequest, TokenResponse
from backend.services.auth_service import AuthService
from backend.utils.config import get_settings
from backend.utils.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
    settings=Depends(get_settings),
    db: Session = Depends(get_db),
):
    if settings.admin_api_key:
        if not x_admin_key or x_admin_key.strip() != settings.admin_api_key.strip():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Valid X-Admin-Key required")
    tenant, raw_key = AuthService.register_tenant(
        name=body.name,
        contact_email=body.contact_email,
        scopes=body.scopes,
        db=db,
    )
    db.commit()
    logger.info("Registered tenant %s (%s)", tenant.id, body.name)
    return RegisterResponse(tenant_id=tenant.id, api_key=raw_key, scopes=body.scopes)


@router.post("/token", response_model=TokenResponse)
def get_token(
    body: TokenRequest,
    db: Session = Depends(get_db),
):
    ctx = AuthService.verify_raw_api_key(body.api_key, db)
    if ctx is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    token = AuthService.create_access_token(tenant_id=ctx.tenant_id, scopes=ctx.scopes)
    return TokenResponse(access_token=token, tenant_id=ctx.tenant_id, scopes=ctx.scopes)
