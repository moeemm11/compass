from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.tables import Permission, Role, SystemSetting, User


def fail(status: int, detail: str) -> None:
    raise HTTPException(status_code=status, detail=detail)


def load_user(db: Session, user_id) -> User | None:
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )


def permission_codes(user: User) -> set[str]:
    return {permission.code for role in user.roles for permission in role.permissions}


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.get(SystemSetting, key)
    return row.value if row else default


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(SystemSetting, key)
    if row is None:
        db.add(SystemSetting(key=key, value=value))
    else:
        row.value = value


def has_permission(user: User, code: str, db: Session) -> bool:
    codes = permission_codes(user)
    if "admin.full" in codes:
        if code == "approvals.decide" and get_setting(db, "admin_can_approve", "true") != "true":
            return "approvals.decide" in codes
        return True
    return code in codes


def effective_permissions(user: User, db: Session) -> list[str]:
    codes = permission_codes(user)
    if "admin.full" not in codes:
        return sorted(codes)
    all_codes = set(db.scalars(select(Permission.code)).all())
    all_codes.add("approvals.decide")
    if get_setting(db, "admin_can_approve", "true") != "true":
        all_codes.discard("approvals.decide")
    return sorted(all_codes)


def has_role(user: User, role_name: str) -> bool:
    if any(role.name == role_name for role in user.roles):
        return True
    return "admin.full" in permission_codes(user)


def require_permission(user: User, db: Session, *codes: str) -> None:
    missing = [code for code in codes if not has_permission(user, code, db)]
    if missing:
        fail(403, "You do not have permission to perform this action")
