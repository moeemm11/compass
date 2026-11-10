"""Red flags escalate attention. They never change the mathematical score."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import CommercialAssessment, Opportunity, OpportunityPartner, RedFlagRule, ResourceRequirement, Risk
from app.services.scoring import to_decimal


def evaluate_red_flags(db: Session, opportunity_id) -> list[dict]:
    rules = db.scalars(select(RedFlagRule).where(RedFlagRule.is_active.is_(True)).order_by(RedFlagRule.display_order)).all()
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        return []
    commercial = db.scalar(
        select(CommercialAssessment)
        .where(CommercialAssessment.opportunity_id == opportunity_id)
        .order_by(CommercialAssessment.updated_at.desc())
    )
    resources = db.scalars(select(ResourceRequirement).where(ResourceRequirement.opportunity_id == opportunity_id)).all()
    risks = db.scalars(
        select(Risk).where(Risk.opportunity_id == opportunity_id, Risk.deleted_at.is_(None))
    ).all()
    partners = db.scalars(select(OpportunityPartner).where(OpportunityPartner.opportunity_id == opportunity_id)).all()
    triggered: list[dict] = []
    for rule in rules:
        params = rule.parameters or {}
        detail = _match(rule.code, params, opportunity, commercial, resources, risks, partners)
        if detail:
            triggered.append(
                {
                    "code": rule.code,
                    "name": rule.name,
                    "description": rule.description,
                    "detail": detail,
                }
            )
    return triggered


def _match(code, params, opportunity, commercial, resources, risks, partners) -> str | None:
    if code == "negative_margin":
        if commercial is not None and to_decimal(commercial.gross_profit) < 0:
            return "Expected gross profit is negative."
        return None
    if code == "missing_partner":
        if not opportunity.partner_required:
            return None
        confirmed = set(params.get("confirmed_statuses") or ["confirmed", "contracted"])
        if any(link.commitment_status in confirmed for link in partners):
            return None
        return "A delivery partner is mandatory and none is confirmed."
    if code == "critical_resource_gap":
        gaps = [item.role for item in resources if item.availability_status == "gap" or item.identified_gap]
        if not gaps:
            return None
        return "Critical resource gap: " + ", ".join(gaps)
    if code == "critical_risk":
        minimum = int(params.get("min_inherent_score", 15))
        titles = [risk.title for risk in risks if risk.status == "open" and risk.inherent_score >= minimum]
        if not titles:
            return None
        return "Open critical risk: " + ", ".join(titles)
    if code == "regulatory_blocker":
        titles = [risk.title for risk in risks if risk.is_regulatory_blocker and risk.status == "open"]
        if not titles:
            return None
        return "Mandatory regulatory requirement is not satisfied: " + ", ".join(titles)
    return None
