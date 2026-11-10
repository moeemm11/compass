import uuid
from datetime import datetime, timezone

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.services.access import fail, load_user

bearer = HTTPBearer(auto_error=False)


def get_db(request: Request):
    db = request.app.state.session_factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    if credentials is None or not credentials.credentials:
        fail(401, "Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, _secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        fail(401, "Invalid or expired session")
    if payload.get("type") != "access":
        fail(401, "Invalid token type")
    user = load_user(db, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        fail(401, "User is inactive or was not found")
    return user


def _secret() -> str:
    from app.core.config import get_settings

    return get_settings().secret_key


def minutes_from_settings(db: Session) -> int:
    from app.core.config import get_settings
    from app.services.access import get_setting

    raw = get_setting(db, "session_minutes", str(get_settings().access_token_minutes))
    try:
        return max(15, min(int(raw), 24 * 60))
    except ValueError:
        return get_settings().access_token_minutes


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
