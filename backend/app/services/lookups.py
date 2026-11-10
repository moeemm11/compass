from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import LookupOption
from app.services.access import fail
from app.services.constants import (
    ACTION_PRIORITIES,
    ACTION_STATUSES,
    AGREEMENT_STATUSES,
    AVAILABILITY_STATUSES,
    COMMITMENT_STATUSES,
    DECISION_VALUES,
    MANUAL_TRANSITIONS,
    NDA_STATUSES,
    OPPORTUNITY_SOURCES,
    OPPORTUNITY_STATUSES,
    PARTNER_STATUSES,
    QUESTION_TYPES,
    RESOURCE_TYPES,
    RISK_CATEGORIES,
    RISK_STATUSES,
    STRATEGIC_IMPORTANCE,
)


def _catalog() -> dict[str, list[tuple[str, dict | None]]]:
    statuses = [(code, {"allowed_transitions": sorted(MANUAL_TRANSITIONS.get(code, set()))}) for code in OPPORTUNITY_STATUSES]
    plain = {
        "opportunity_source": [(code, None) for code in OPPORTUNITY_SOURCES],
        "opportunity_status": statuses,
        "strategic_importance": [(code, None) for code in STRATEGIC_IMPORTANCE],
        "risk_category": [(code, None) for code in RISK_CATEGORIES],
        "risk_status": [(code, None) for code in RISK_STATUSES],
        "action_status": [(code, None) for code in ACTION_STATUSES],
        "action_priority": [(code, None) for code in ACTION_PRIORITIES],
        "partner_status": [(code, None) for code in PARTNER_STATUSES],
        "nda_status": [(code, None) for code in NDA_STATUSES],
        "agreement_status": [(code, None) for code in AGREEMENT_STATUSES],
        "commitment_status": [(code, None) for code in COMMITMENT_STATUSES],
        "resource_type": [(code, None) for code in RESOURCE_TYPES],
        "availability_status": [(code, None) for code in AVAILABILITY_STATUSES],
        "decision": [(code, None) for code in DECISION_VALUES],
        "question_type": [(code, None) for code in QUESTION_TYPES],
    }
    return plain


def ensure_lookup_options(db: Session) -> None:
    """Insert the default lists once. Later edits in the database are left in place."""
    existing = set(db.scalars(select(LookupOption.category).distinct()).all())
    for category, items in _catalog().items():
        if category in existing:
            continue
        for order, (code, details) in enumerate(items):
            db.add(
                LookupOption(
                    category=category,
                    code=code,
                    label=code,
                    sort_order=order,
                    is_active=True,
                    details=details,
                )
            )
    db.flush()


def codes(db: Session, category: str) -> list[str]:
    return list(
        db.scalars(
            select(LookupOption.code)
            .where(LookupOption.category == category, LookupOption.is_active.is_(True))
            .order_by(LookupOption.sort_order, LookupOption.code)
        ).all()
    )


def require_code(db: Session, category: str, value: str | None, message: str) -> None:
    if value not in codes(db, category):
        fail(400, message)


def allowed_transitions(db: Session, status: str) -> set[str]:
    row = db.scalar(
        select(LookupOption).where(
            LookupOption.category == "opportunity_status",
            LookupOption.code == status,
            LookupOption.is_active.is_(True),
        )
    )
    if row is None or not row.details:
        return set()
    return set(row.details.get("allowed_transitions") or [])


def grouped(db: Session) -> dict[str, list[str]]:
    rows = db.scalars(
        select(LookupOption).where(LookupOption.is_active.is_(True)).order_by(LookupOption.sort_order, LookupOption.code)
    ).all()
    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row.category, []).append(row.code)
    return result
