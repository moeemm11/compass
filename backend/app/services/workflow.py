from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import (
    ActionItem,
    ApprovalRecord,
    Assessment,
    ManagementDecision,
    Opportunity,
    RecommendationRule,
    utcnow,
)
from app.services.access import fail, has_permission, has_role
from app.services.assessments import can_view_opportunity, get_assessment
from app.services.red_flags import evaluate_red_flags
from app.services.lookups import require_code
from app.services.records import audit, notify, notify_roles
from app.services.scoring import to_decimal


def latest_review(db: Session, assessment_id, stage: str) -> ApprovalRecord | None:
    return db.scalar(
        select(ApprovalRecord)
        .where(ApprovalRecord.assessment_id == assessment_id, ApprovalRecord.stage == stage)
        .order_by(ApprovalRecord.decided_at.desc())
    )


def record_review(db: Session, user, assessment_id, stage: str, decision: str, comments: str) -> ApprovalRecord:
    if stage == "functional_review":
        if not has_role(user, "Functional Reviewer"):
            fail(403, "Only a functional reviewer can complete this stage")
    elif stage == "commercial_review":
        if not has_role(user, "Commercial Reviewer"):
            fail(403, "Only a commercial reviewer can complete this stage")
    else:
        fail(400, "Unknown review stage")
    if decision not in {"confirmed", "request_information"}:
        fail(400, "Review decision must be confirmed or request_information")
    if not comments or len(comments.strip()) < 5:
        fail(400, "Review comments are required")
    assessment = get_assessment(db, assessment_id)
    opportunity = db.get(Opportunity, assessment.opportunity_id)
    if not can_view_opportunity(db, user, opportunity):
        fail(403, "You do not have permission to review this assessment")
    if assessment.status != "submitted":
        fail(409, "This assessment is not waiting for review")
    functional = latest_review(db, assessment.id, "functional_review")
    if stage == "commercial_review" and (functional is None or functional.decision != "confirmed"):
        fail(409, "Functional review must be confirmed before commercial review")
    previous = opportunity.status
    if decision == "request_information":
        assessment.status = "returned"
        assessment.recommendation_final = False
        opportunity.status = "under_assessment"
    elif stage == "functional_review":
        opportunity.status = "under_review"
        assessment.status = "submitted"
    else:
        opportunity.status = "awaiting_executive_decision"
        assessment.status = "pending_approval"
        notify_roles(
            db,
            ["Executive Approver"],
            "Executive decision required",
            f"{assessment.assessment_number} is ready for an executive decision.",
            notification_type="approval",
            entity_type="assessment",
            entity_id=assessment.id,
        )
    record = ApprovalRecord(
        opportunity_id=opportunity.id,
        assessment_id=assessment.id,
        stage=stage,
        approver_id=user.id,
        decision=decision,
        comments=comments.strip(),
        previous_status=previous,
        new_status=opportunity.status,
    )
    db.add(record)
    db.flush()
    audit(
        db,
        user_id=user.id,
        entity_type="assessment",
        entity_id=assessment.id,
        action="assessment.reviewed",
        opportunity_id=opportunity.id,
        new={"stage": stage, "decision": decision, "status": opportunity.status},
    )
    return record


def record_decision(db: Session, user, assessment_id, payload) -> ManagementDecision:
    if not has_permission(user, "approvals.decide", db):
        fail(403, "You do not have permission to record an executive decision")
    assessment = get_assessment(db, assessment_id)
    opportunity = db.get(Opportunity, assessment.opportunity_id)
    if assessment.status != "pending_approval":
        fail(409, "This assessment is not awaiting an executive decision")
    decision = payload.decision
    require_code(db, "decision", decision, "Decision is not recognised")
    if not payload.comments or len(payload.comments.strip()) < 5:
        fail(400, "Decision comments are required")
    flags = evaluate_red_flags(db, assessment.opportunity_id) or assessment.submitted_red_flags or []
    if decision in {"approved", "conditionally_approved"} and flags and len((payload.exception_justification or "").strip()) < 10:
        fail(400, "Active red flags require an exception justification before this opportunity can be approved")
    rules = db.scalars(select(RecommendationRule).where(RecommendationRule.template_version_id == assessment.template_version_id)).all()
    names = {rule.recommendation_name for rule in rules}
    override = (payload.override_recommendation or "").strip() or None
    if override and override not in names:
        fail(400, "The override must use a recommendation configured on this template")
    is_override = bool(override and override != assessment.recommendation_name)
    if is_override and len((payload.override_reason or "").strip()) < 10:
        fail(400, "Overriding the system recommendation requires a justification")
    previous = opportunity.status
    status_map = {
        "approved": "approved",
        "conditionally_approved": "conditionally_approved",
        "on_hold": "on_hold",
        "rejected": "rejected",
        "returned": "under_assessment",
    }
    opportunity.status = status_map[decision]
    if decision == "returned":
        assessment.status = "returned"
        assessment.recommendation_final = False
    else:
        assessment.status = "decided"
    if payload.mandatory_action_ids:
        actions = db.scalars(select(ActionItem).where(ActionItem.id.in_(payload.mandatory_action_ids))).all()
        for action in actions:
            if action.opportunity_id == opportunity.id:
                action.is_mandatory_for_commitment = True
    approval = ApprovalRecord(
        opportunity_id=opportunity.id,
        assessment_id=assessment.id,
        stage="executive_decision",
        approver_id=user.id,
        decision=decision,
        comments=payload.comments.strip(),
        previous_status=previous,
        new_status=opportunity.status,
    )
    management = ManagementDecision(
        opportunity_id=opportunity.id,
        assessment_id=assessment.id,
        calculated_recommendation=assessment.recommendation_name or "",
        calculated_score=assessment.calculated_score,
        final_decision=decision,
        override_recommendation=override,
        override_reason=(payload.override_reason or "").strip(),
        is_override=is_override,
        exception_justification=(payload.exception_justification or "").strip(),
        decision_maker_id=user.id,
        decision_date=utcnow(),
    )
    db.add(approval)
    db.add(management)
    db.flush()
    audit(
        db,
        user_id=user.id,
        entity_type="decision",
        entity_id=management.id,
        action="decision.recorded",
        opportunity_id=opportunity.id,
        new={
            "decision": decision,
            "recommendation": assessment.recommendation_name,
            "override": override,
            "is_override": is_override,
            "score": format(to_decimal(assessment.calculated_score), "f") if assessment.calculated_score is not None else None,
        },
    )
    notify(
        db,
        opportunity.owner_id,
        "Executive decision recorded",
        f"{opportunity.reference_number} was marked {decision.replace('_', ' ')}.",
        "decision",
        "opportunity",
        opportunity.id,
    )
    return management


def pending_items(db: Session, user) -> list[dict]:
    from app.services.records import status_label

    assessments = db.scalars(select(Assessment).where(Assessment.status.in_(["submitted", "pending_approval"]))).all()
    items = []
    for assessment in assessments:
        opportunity = db.get(Opportunity, assessment.opportunity_id)
        if opportunity.deleted_at is not None or not can_view_opportunity(db, user, opportunity):
            continue
        functional = latest_review(db, assessment.id, "functional_review")
        commercial = latest_review(db, assessment.id, "commercial_review")
        stage = None
        if assessment.status == "submitted" and (functional is None or functional.decision != "confirmed"):
            stage = "functional_review"
            allowed = has_role(user, "Functional Reviewer")
        elif assessment.status == "submitted" and (commercial is None or commercial.decision != "confirmed"):
            stage = "commercial_review"
            allowed = has_role(user, "Commercial Reviewer")
        elif assessment.status == "pending_approval":
            stage = "executive_decision"
            allowed = has_permission(user, "approvals.decide", db)
        else:
            allowed = False
        if stage and allowed:
            items.append(
                {
                    "assessment_id": str(assessment.id),
                    "assessment_number": assessment.assessment_number,
                    "opportunity_id": str(opportunity.id),
                    "opportunity_name": opportunity.name,
                    "reference_number": opportunity.reference_number,
                    "stage": stage,
                    "stage_label": status_label(stage),
                    "score": float(assessment.calculated_score) if assessment.calculated_score is not None else None,
                    "recommendation": assessment.recommendation_name,
                    "submitted_at": assessment.submitted_at.isoformat() if assessment.submitted_at else None,
                }
            )
    return items
