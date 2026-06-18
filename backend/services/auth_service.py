import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.api_key import ApiKey
from backend.models.tenant import Tenant
from backend.utils.config import get_settings

ALGORITHM = "HS256"


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _generate_api_key() -> tuple[str, str, str]:
    raw = f"vps_{secrets.token_hex(24)}"
    prefix = raw[:10]
    key_hash = _hash_key(raw)
    return raw, prefix, key_hash


class AuthContext:
    def __init__(self, tenant_id: str, scopes: list[str], token_type: str):
        self.tenant_id = tenant_id
        self.scopes = scopes
        self.token_type = token_type


class AuthService:

    @staticmethod
    def register_tenant(name: str, contact_email: str | None = None, scopes: str = "query", db: Session | None = None) -> tuple[Tenant, str]:
        tenant_id = secrets.token_hex(16)
        tenant = Tenant(id=tenant_id, name=name, contact_email=contact_email)
        if db is not None:
            db.add(tenant)
            db.flush()
        raw_key, prefix, key_hash = _generate_api_key()
        api_key = ApiKey(
            id=secrets.token_hex(16),
            tenant_id=tenant_id,
            prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
        )
        if db is not None:
            db.add(api_key)
            db.flush()
        return tenant, raw_key

    @staticmethod
    def create_api_key(tenant_id: str, scopes: str = "query", db: Session | None = None) -> tuple[ApiKey, str]:
        raw_key, prefix, key_hash = _generate_api_key()
        api_key = ApiKey(
            id=secrets.token_hex(16),
            tenant_id=tenant_id,
            prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
        )
        if db is not None:
            db.add(api_key)
            db.flush()
        return api_key, raw_key

    @staticmethod
    def verify_raw_api_key(raw_key: str, db: Session) -> AuthContext | None:
        prefix = raw_key[:10]
        key_hash = _hash_key(raw_key)
        row = db.scalar(
            select(ApiKey).where(
                ApiKey.prefix == prefix,
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True,
            )
        )
        if row is None:
            return None
        tenant = db.get(Tenant, row.tenant_id)
        if tenant is None or not tenant.is_active:
            return None
        scopes = [s.strip() for s in row.scopes.split(",")]
        return AuthContext(tenant_id=row.tenant_id, scopes=scopes, token_type="api_key")

    @staticmethod
    def create_access_token(tenant_id: str, scopes: list[str], expires_delta: timedelta | None = None) -> str:
        settings = get_settings()
        payload = {
            "sub": tenant_id,
            "scopes": scopes,
            "iat": datetime.now(timezone.utc),
        }
        if expires_delta is None:
            expires_delta = timedelta(hours=settings.jwt_expiry_hours)
        payload["exp"] = datetime.now(timezone.utc) + expires_delta
        return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

    @staticmethod
    def decode_access_token(token: str) -> AuthContext | None:
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
            tenant_id: str | None = payload.get("sub")
            scopes_raw: list | None = payload.get("scopes")
            if tenant_id is None or scopes_raw is None:
                return None
            return AuthContext(tenant_id=tenant_id, scopes=list(scopes_raw), token_type="jwt")
        except JWTError:
            return None
