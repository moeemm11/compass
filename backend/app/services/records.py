import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import ActionItem, Assessment, AuditLog, Notification, Opportunity, Risk, utcnow


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def audit(
    db: Session,
    *,
    user_id,
    entity_type: str,
    entity_id,
    action: str,
    old=None,
    new=None,
    opportunity_id=None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            opportunity_id=opportunity_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            action=action,
            old_values=jsonable(old),
            new_values=jsonable(new),
        )
    )


def notify(
    db: Session,
    user_id,
    title: str,
    message: str,
    notification_type: str = "info",
    entity_type: str | None = None,
    entity_id=None,
) -> None:
    if not user_id:
        return
    db.add(
        Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
        )
    )


def notify_roles(db: Session, role_names: list[str], title: str, message: str, **kwargs) -> None:
    from app.models.tables import Role, User

    users = db.scalars(
        select(User).join(User.roles).where(Role.name.in_(role_names), User.is_active.is_(True))
    ).all()
    seen = set()
    for user in users:
        if user.id in seen:
            continue
        seen.add(user.id)
        notify(db, user.id, title, message, **kwargs)


def next_reference(db: Session, prefix: str, model, attribute: str) -> str:
    year = datetime.now().year
    column = getattr(model, attribute)
    existing = db.scalars(select(column).where(column.like(f"{prefix}-{year}-%"))).all()
    highest = 0
    for value in existing:
        highest = max(highest, _suffix(value))
    for obj in db.new:
        if isinstance(obj, model):
            highest = max(highest, _suffix(getattr(obj, attribute, "")))
    return f"{prefix}-{year}-{highest + 1:04d}"


def _suffix(value) -> int:
    try:
        return int(str(value).rsplit("-", 1)[-1])
    except (TypeError, ValueError):
        return 0


def status_label(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("_", " ").title()


ACTION_SUMMARIES = {
    "opportunity.created": "Registered the opportunity",
    "opportunity.updated": "Updated opportunity details",
    "opportunity.archived": "Archived the opportunity",
    "opportunity.transition": "Changed the opportunity status",
    "assessment.created": "Created an assessment",
    "assessment.updated": "Updated assessment scores",
    "assessment.submitted": "Submitted the assessment",
    "assessment.reviewed": "Recorded a review",
    "decision.recorded": "Recorded a management decision",
    "template.created": "Created an assessment template",
    "template.updated": "Updated a draft template",
    "template.published": "Published an assessment template version",
    "template.versioned": "Started a new template version",
    "risk.saved": "Updated the risk register",
    "commercial.saved": "Updated the commercial assessment",
    "partner.linked": "Linked a partner",
    "resource.saved": "Updated resource requirements",
    "action.saved": "Updated an action",
    "user.changed": "Changed a user account",
    "settings.changed": "Changed system settings",
}


def opportunity_for(db: Session, entity_type: str, entity_id: str):
    try:
        parsed = uuid.UUID(entity_id)
    except ValueError:
        return None
    if entity_type == "opportunity":
        return parsed
    if entity_type == "assessment":
        row = db.get(Assessment, parsed)
        return row.opportunity_id if row else None
    if entity_type == "risk":
        row = db.get(Risk, parsed)
        return row.opportunity_id if row else None
    if entity_type == "action":
        row = db.get(ActionItem, parsed)
        return row.opportunity_id if row else None
    return None


def touch_opportunity(db: Session, opportunity_id) -> None:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity:
        opportunity.updated_at = utcnow()
