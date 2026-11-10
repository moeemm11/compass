from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.tables import (
    ActionItem,
    Assessment,
    AssessmentAssignment,
    AssessmentEvidence,
    AssessmentQuestion,
    AssessmentTemplate,
    AssessmentTemplateVersion,
    CriterionScore,
    EvaluationCriterion,
    EvaluationSubcriterion,
    Opportunity,
    QuestionResponse,
    RecommendationRule,
    ScoringScale,
    ScoringScaleValue,
    SubcriterionScore,
    User,
    utcnow,
)
from app.services.access import fail, has_permission
from app.services.constants import EDITABLE_ASSESSMENT_STATUSES
from app.services.lookups import codes
from app.services.recommendation import RecommendationBand, match_recommendation
from app.services.records import audit, next_reference, notify
from app.services.red_flags import evaluate_red_flags
from app.services.scoring import CriterionInput, SubcriterionInput, display_score, overall_score, score_criterion, to_decimal
from app.services.templates import present_version, published_version, validate_version


def get_assessment(db: Session, assessment_id) -> Assessment:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        fail(404, "Assessment was not found")
    return assessment


def can_view_opportunity(db: Session, user: User, opportunity: Opportunity) -> bool:
    if has_permission(user, "opportunities.view_all", db):
        return True
    if not has_permission(user, "opportunities.view_assigned", db):
        return False
    if opportunity.owner_id == user.id:
        return True
    assigned = db.scalar(
        select(AssessmentAssignment.id)
        .join(Assessment, Assessment.id == AssessmentAssignment.assessment_id)
        .where(Assessment.opportunity_id == opportunity.id, AssessmentAssignment.user_id == user.id)
    )
    return assigned is not None


def can_edit_opportunity(db: Session, user: User, opportunity: Opportunity) -> bool:
    if opportunity.deleted_at is not None:
        return False
    if has_permission(user, "opportunities.edit_any", db):
        return True
    return has_permission(user, "opportunities.edit_own", db) and opportunity.owner_id == user.id


def can_score(db: Session, user: User, assessment: Assessment, criterion_id=None) -> bool:
    if assessment.status not in EDITABLE_ASSESSMENT_STATUSES:
        return False
    opportunity = db.get(Opportunity, assessment.opportunity_id)
    if has_permission(user, "assessments.complete_any", db) or can_edit_opportunity(db, user, opportunity):
        return True
    if not has_permission(user, "assessments.complete_assigned", db):
        return False
    assignments = db.scalars(
        select(AssessmentAssignment).where(
            AssessmentAssignment.assessment_id == assessment.id,
            AssessmentAssignment.user_id == user.id,
        )
    ).all()
    if any(item.criterion_id is None for item in assignments):
        return True
    if criterion_id is None:
        return bool(assignments)
    return any(item.criterion_id == criterion_id for item in assignments)


def create_assessment(db: Session, user: User, opportunity: Opportunity, template_id, parent_assessment_id=None) -> Assessment:
    if not can_edit_opportunity(db, user, opportunity) and not has_permission(user, "assessments.complete_any", db):
        fail(403, "You do not have permission to start an assessment for this opportunity")
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        fail(404, "Assessment template was not found")
    version = published_version(db, template)
    if version is None:
        fail(400, "Select a published assessment template")
    errors = validate_version(db, version)
    if errors:
        fail(400, "The published template is invalid. " + " ".join(errors))
    if parent_assessment_id:
        parent = get_assessment(db, parent_assessment_id)
        if parent.opportunity_id != opportunity.id:
            fail(400, "A reassessment must belong to the same opportunity")
    assessment = Assessment(
        opportunity_id=opportunity.id,
        template_version_id=version.id,
        assessment_number=next_reference(db, "ASM", Assessment, "assessment_number"),
        status="draft",
        created_by=user.id,
        parent_assessment_id=parent_assessment_id,
    )
    db.add(assessment)
    if opportunity.status in {"identified", "under_qualification", "on_hold"}:
        opportunity.status = "under_assessment"
    audit(
        db,
        user_id=user.id,
        entity_type="assessment",
        entity_id=assessment.id,
        action="assessment.created",
        opportunity_id=opportunity.id,
        new={"template_version_id": str(version.id), "parent_assessment_id": str(parent_assessment_id) if parent_assessment_id else None},
    )
    db.flush()
    return assessment


def update_assessment(db: Session, user: User, assessment: Assessment, payload) -> Assessment:
    if assessment.status not in EDITABLE_ASSESSMENT_STATUSES:
        fail(409, "This assessment is locked. Request a reassessment before changing scores.")
    opportunity = db.get(Opportunity, assessment.opportunity_id)
    if payload.assignments is not None:
        if not (has_permission(user, "assessments.complete_any", db) or can_edit_opportunity(db, user, opportunity)):
            fail(403, "You do not have permission to assign evaluators")
        db.execute(delete(AssessmentAssignment).where(AssessmentAssignment.assessment_id == assessment.id))
        for item in payload.assignments:
            assignee = db.get(User, item.user_id)
            if assignee is None or not assignee.is_active:
                fail(400, "Each assignment needs an active user")
            db.add(
                AssessmentAssignment(
                    assessment_id=assessment.id,
                    user_id=item.user_id,
                    criterion_id=item.criterion_id,
                )
            )
            notify(
                db,
                item.user_id,
                "Assessment assigned",
                f"You were assigned to {assessment.assessment_number}.",
                "assignment",
                "assessment",
                assessment.id,
            )
    if payload.criterion_scores:
        for item in payload.criterion_scores:
            if not can_score(db, user, assessment, item.criterion_id):
                fail(403, "You can only score criteria assigned to you")
            row = _criterion_row(db, assessment.id, item.criterion_id)
            row.comments = item.comments or ""
            row.gaps = item.gaps or ""
            row.evaluator_id = user.id
            row.evaluated_at = utcnow()
            if item.selected_score is not None or "selected_score" in item.model_fields_set:
                criterion = db.get(EvaluationCriterion, item.criterion_id)
                active_subs = [sub for sub in criterion.subcriteria if sub.is_active] if criterion else []
                if not active_subs:
                    _validate_choice(db, assessment, item.selected_score)
                    row.selected_score = to_decimal(item.selected_score) if item.selected_score is not None else None
    if payload.subcriterion_scores:
        for item in payload.subcriterion_scores:
            sub = db.get(EvaluationSubcriterion, item.subcriterion_id)
            if sub is None:
                fail(400, "A subcriterion does not belong to this assessment")
            if not can_score(db, user, assessment, sub.criterion_id):
                fail(403, "You can only score criteria assigned to you")
            _validate_choice(db, assessment, item.selected_score)
            row = _sub_row(db, assessment.id, sub.id)
            row.selected_score = to_decimal(item.selected_score) if item.selected_score is not None else None
            row.comments = item.comments or ""
            row.evaluator_id = user.id
            row.evaluated_at = utcnow()
    if payload.responses:
        if not can_score(db, user, assessment, None) and not has_permission(user, "assessments.complete_any", db):
            fail(403, "You do not have permission to answer this assessment")
        for item in payload.responses:
            question = db.get(AssessmentQuestion, item.question_id)
            if question is None or question.template_version_id != assessment.template_version_id:
                fail(400, "A question does not belong to this assessment")
            row = db.scalar(
                select(QuestionResponse).where(
                    QuestionResponse.assessment_id == assessment.id,
                    QuestionResponse.question_id == question.id,
                )
            )
            if row is None:
                row = QuestionResponse(assessment_id=assessment.id, question_id=question.id)
                db.add(row)
            row.response_text = item.response_text or ""
            row.response_json = item.response_json
    if assessment.status == "draft":
        assessment.status = "in_progress"
    recalculate(db, assessment)
    audit(
        db,
        user_id=user.id,
        entity_type="assessment",
        entity_id=assessment.id,
        action="assessment.updated",
        opportunity_id=assessment.opportunity_id,
        new={"completion": str(assessment.completion_percentage)},
    )
    return assessment


def submit_assessment(db: Session, user: User, assessment: Assessment) -> Assessment:
    opportunity = db.get(Opportunity, assessment.opportunity_id)
    if not (has_permission(user, "assessments.complete_any", db) or can_edit_opportunity(db, user, opportunity)):
        fail(403, "You do not have permission to submit this assessment")
    if assessment.status not in EDITABLE_ASSESSMENT_STATUSES:
        fail(409, "This assessment has already been submitted")
    recalculate(db, assessment)
    blockers = blocking_reasons(db, assessment)
    if blockers:
        fail(400, "The assessment cannot be submitted. " + " ".join(blockers))
    flags = evaluate_red_flags(db, assessment.opportunity_id)
    assessment.status = "submitted"
    assessment.recommendation_final = True
    assessment.submitted_by = user.id
    assessment.submitted_at = utcnow()
    assessment.submitted_red_flags = flags
    opportunity = db.get(Opportunity, assessment.opportunity_id)
    opportunity.status = "under_review"
    _ensure_gap_actions(db, assessment, user)
    audit(
        db,
        user_id=user.id,
        entity_type="assessment",
        entity_id=assessment.id,
        action="assessment.submitted",
        opportunity_id=opportunity.id,
        new={
            "score": format(assessment.calculated_score, "f") if assessment.calculated_score is not None else None,
            "recommendation": assessment.recommendation_name,
            "red_flags": [flag["code"] for flag in flags],
        },
    )
    from app.services.records import notify_roles

    notify_roles(
        db,
        ["Functional Reviewer", "Commercial Reviewer", "Executive Approver"],
        "Assessment submitted",
        f"{assessment.assessment_number} is ready for review.",
        notification_type="review",
        entity_type="assessment",
        entity_id=assessment.id,
    )
    return assessment


def recalculate(db: Session, assessment: Assessment) -> None:
    version = db.get(AssessmentTemplateVersion, assessment.template_version_id)
    criteria = db.scalars(
        select(EvaluationCriterion)
        .where(EvaluationCriterion.template_version_id == version.id, EvaluationCriterion.is_active.is_(True))
        .options(selectinload(EvaluationCriterion.subcriteria))
        .order_by(EvaluationCriterion.display_order)
    ).all()
    scale = db.scalar(select(ScoringScale).where(ScoringScale.template_version_id == version.id).options(selectinload(ScoringScale.values)))
    maximum = to_decimal(scale.maximum_value)
    sub_scores = {
        row.subcriterion_id: row
        for row in db.scalars(select(SubcriterionScore).where(SubcriterionScore.assessment_id == assessment.id)).all()
    }
    results = []
    completed_points = 0
    total_points = 0
    for criterion in criteria:
        active_subs = [sub for sub in criterion.subcriteria if sub.is_active]
        if active_subs:
            sub_inputs = []
            for sub in active_subs:
                total_points += 1
                saved = sub_scores.get(sub.id)
                selected = saved.selected_score if saved else None
                if selected is not None:
                    completed_points += 1
                    value = _match_scale_value(scale.values, selected)
                    if value and value.requires_justification:
                        total_points += 1
                        if saved and (saved.comments or "").strip():
                            completed_points += 1
                sub_inputs.append(
                    SubcriterionInput(
                        weight=to_decimal(sub.weight),
                        selected_score=to_decimal(selected) if selected is not None else None,
                    )
                )
            result = score_criterion(CriterionInput(weight=to_decimal(criterion.weight), subcriteria=sub_inputs), maximum)
        else:
            total_points += 1
            row = _criterion_row(db, assessment.id, criterion.id)
            selected = row.selected_score
            if selected is not None:
                completed_points += 1
                value = _match_scale_value(scale.values, selected)
                if value and value.requires_justification:
                    total_points += 1
                    if (row.comments or "").strip():
                        completed_points += 1
            result = score_criterion(
                CriterionInput(
                    weight=to_decimal(criterion.weight),
                    selected_score=to_decimal(selected) if selected is not None else None,
                ),
                maximum,
            )
        if criterion.requires_evidence:
            total_points += 1
            evidence = db.scalar(
                select(AssessmentEvidence.id).where(
                    AssessmentEvidence.assessment_id == assessment.id,
                    AssessmentEvidence.criterion_id == criterion.id,
                )
            )
            if evidence:
                completed_points += 1
        stored = _criterion_row(db, assessment.id, criterion.id)
        stored.selected_score = result.selected_score
        stored.normalized_score = result.normalized_score
        stored.weighted_score = result.weighted_score
        if active_subs:
            for sub in active_subs:
                saved = sub_scores.get(sub.id)
                if saved and saved.selected_score is not None:
                    saved.normalized_score = to_decimal(saved.selected_score) / maximum
        results.append(result)

    questions = db.scalars(
        select(AssessmentQuestion).where(
            AssessmentQuestion.template_version_id == version.id,
            AssessmentQuestion.is_active.is_(True),
            AssessmentQuestion.is_mandatory.is_(True),
        )
    ).all()
    responses = {
        row.question_id: row
        for row in db.scalars(select(QuestionResponse).where(QuestionResponse.assessment_id == assessment.id)).all()
    }
    for question in questions:
        total_points += 1
        response = responses.get(question.id)
        if response and ((response.response_text or "").strip() or response.response_json):
            completed_points += 1

    total_score, scores_complete = overall_score(results)
    assessment.calculated_score = total_score
    assessment.scores_complete = scores_complete
    assessment.completion_percentage = Decimal("0") if total_points == 0 else (Decimal(completed_points) / Decimal(total_points) * Decimal("100"))
    blockers = _score_blockers(version, criteria, results, questions, responses, db, assessment, scale)
    if scores_complete and not blockers:
        rules = db.scalars(select(RecommendationRule).where(RecommendationRule.template_version_id == version.id)).all()
        band = match_recommendation(
            total_score,
            [
                RecommendationBand(
                    name=rule.recommendation_name,
                    minimum_score=to_decimal(rule.minimum_score),
                    maximum_score=to_decimal(rule.maximum_score),
                    description=rule.description,
                    management_action=rule.management_action,
                    color=rule.color,
                    priority=rule.priority,
                )
                for rule in rules
            ],
        )
        assessment.recommendation_name = band.name
    else:
        assessment.recommendation_name = None
        if assessment.status in EDITABLE_ASSESSMENT_STATUSES:
            assessment.recommendation_final = False


def blocking_reasons(db: Session, assessment: Assessment) -> list[str]:
    version = db.get(AssessmentTemplateVersion, assessment.template_version_id)
    if version is None or version.status not in {"published", "superseded"}:
        return ["The assessment is not based on a published template."]
    errors = []
    if version.status == "published":
        errors.extend(validate_version(db, version))
    criteria = db.scalars(
        select(EvaluationCriterion)
        .where(EvaluationCriterion.template_version_id == version.id, EvaluationCriterion.is_active.is_(True))
        .options(selectinload(EvaluationCriterion.subcriteria))
    ).all()
    scale = db.scalar(select(ScoringScale).where(ScoringScale.template_version_id == version.id).options(selectinload(ScoringScale.values)))
    sub_scores = {
        row.subcriterion_id: row
        for row in db.scalars(select(SubcriterionScore).where(SubcriterionScore.assessment_id == assessment.id)).all()
    }
    responses = {
        row.question_id: row
        for row in db.scalars(select(QuestionResponse).where(QuestionResponse.assessment_id == assessment.id)).all()
    }
    questions = db.scalars(
        select(AssessmentQuestion).where(
            AssessmentQuestion.template_version_id == version.id,
            AssessmentQuestion.is_mandatory.is_(True),
            AssessmentQuestion.is_active.is_(True),
        )
    ).all()
    for criterion in criteria:
        active_subs = [sub for sub in criterion.subcriteria if sub.is_active]
        if active_subs:
            for sub in active_subs:
                saved = sub_scores.get(sub.id)
                if saved is None or saved.selected_score is None:
                    errors.append(f"{criterion.name} / {sub.name} still needs a score.")
                elif _needs_justification(scale, saved.selected_score) and not (saved.comments or "").strip():
                    errors.append(f"{sub.name} requires a justification for the selected rating.")
        else:
            row = db.scalar(
                select(CriterionScore).where(CriterionScore.assessment_id == assessment.id, CriterionScore.criterion_id == criterion.id)
            )
            if row is None or row.selected_score is None:
                errors.append(f"{criterion.name} still needs a score.")
            elif _needs_justification(scale, row.selected_score) and not (row.comments or "").strip():
                errors.append(f"{criterion.name} requires a justification for the selected rating.")
        if criterion.requires_evidence:
            evidence = db.scalar(
                select(AssessmentEvidence.id).where(
                    AssessmentEvidence.assessment_id == assessment.id,
                    AssessmentEvidence.criterion_id == criterion.id,
                )
            )
            if evidence is None:
                errors.append(f"{criterion.name} requires evidence before submission.")
    for question in questions:
        response = responses.get(question.id)
        if response is None or not ((response.response_text or "").strip() or response.response_json):
            errors.append(f"Mandatory question still needs an answer: {question.prompt}")
    return errors


def _score_blockers(version, criteria, results, questions, responses, db, assessment, scale) -> list[str]:
    if not all(result.complete for result in results):
        return ["Scores are incomplete."]
    reasons = []
    sub_scores = {
        row.subcriterion_id: row
        for row in db.scalars(select(SubcriterionScore).where(SubcriterionScore.assessment_id == assessment.id)).all()
    }
    for criterion in criteria:
        active_subs = [sub for sub in criterion.subcriteria if sub.is_active]
        if active_subs:
            for sub in active_subs:
                saved = sub_scores.get(sub.id)
                if saved and saved.selected_score is not None and _needs_justification(scale, saved.selected_score) and not (saved.comments or "").strip():
                    reasons.append("justification")
        if criterion.requires_evidence:
            evidence = db.scalar(
                select(AssessmentEvidence.id).where(
                    AssessmentEvidence.assessment_id == assessment.id,
                    AssessmentEvidence.criterion_id == criterion.id,
                )
            )
            if evidence is None:
                reasons.append("evidence")
    for question in questions:
        response = responses.get(question.id)
        if response is None or not ((response.response_text or "").strip() or response.response_json):
            reasons.append("question")
    template_errors = validate_version(db, version) if version.status == "published" else []
    return reasons + template_errors


def present_assessment(db: Session, user: User, assessment: Assessment) -> dict:
    opportunity = db.get(Opportunity, assessment.opportunity_id)
    if not can_view_opportunity(db, user, opportunity):
        fail(403, "You do not have permission to view this assessment")
    recalculate(db, assessment)
    version = db.get(AssessmentTemplateVersion, assessment.template_version_id)
    template = db.get(AssessmentTemplate, version.template_id)
    presented = present_version(db, version)
    scale = presented["scale"]
    maximum = Decimal(str(scale["maximum_value"]))
    threshold = to_decimal(version.gap_normalized_threshold)
    criterion_rows = {
        row.criterion_id: row
        for row in db.scalars(select(CriterionScore).where(CriterionScore.assessment_id == assessment.id)).all()
    }
    sub_rows = {
        row.subcriterion_id: row
        for row in db.scalars(select(SubcriterionScore).where(SubcriterionScore.assessment_id == assessment.id)).all()
    }
    evidence = db.scalars(select(AssessmentEvidence).where(AssessmentEvidence.assessment_id == assessment.id)).all()
    responses = {
        row.question_id: row
        for row in db.scalars(select(QuestionResponse).where(QuestionResponse.assessment_id == assessment.id)).all()
    }
    questions = db.scalars(
        select(AssessmentQuestion)
        .where(AssessmentQuestion.template_version_id == version.id)
        .order_by(AssessmentQuestion.display_order)
    ).all()
    assignments = db.scalars(select(AssessmentAssignment).where(AssessmentAssignment.assessment_id == assessment.id)).all()
    gaps = []
    strengths = []
    criteria_out = []
    for criterion in presented["criteria"]:
        if not criterion["is_active"]:
            continue
        stored = criterion_rows.get(_uuid(criterion["id"]))
        subs_out = []
        for sub in criterion["subcriteria"]:
            if not sub["is_active"]:
                continue
            saved = sub_rows.get(_uuid(sub["id"]))
            subs_out.append(
                {
                    **sub,
                    "selected_score": _float(saved.selected_score) if saved else None,
                    "comments": saved.comments if saved else "",
                }
            )
        normalized = to_decimal(stored.normalized_score) if stored and stored.normalized_score is not None else None
        entry = {
            **criterion,
            "subcriteria": subs_out,
            "selected_score": _float(stored.selected_score) if stored else None,
            "normalized_score": _float(stored.normalized_score) if stored else None,
            "weighted_score": _float(display_score(stored.weighted_score)) if stored and stored.weighted_score is not None else None,
            "weighted_score_exact": format(to_decimal(stored.weighted_score), "f") if stored and stored.weighted_score is not None else None,
            "comments": stored.comments if stored else "",
            "gaps": stored.gaps if stored else "",
        }
        criteria_out.append(entry)
        if normalized is not None:
            if normalized <= threshold:
                gaps.append(
                    {
                        "criterion_id": criterion["id"],
                        "criterion_name": criterion["name"],
                        "score": entry["selected_score"],
                        "maximum": float(maximum),
                        "severity": "weak" if normalized <= Decimal("0.4") else "gap",
                        "summary": f"{criterion['name']} scored {entry['selected_score']} of {float(maximum)}.",
                        "suggestion": f"Close the gap in {criterion['name']} before Diyar commits commercial or delivery resources.",
                    }
                )
            elif normalized >= Decimal("0.8"):
                strengths.append({"criterion_name": criterion["name"], "score": entry["selected_score"]})
    rule = db.scalar(
        select(RecommendationRule).where(
            RecommendationRule.template_version_id == version.id,
            RecommendationRule.recommendation_name == assessment.recommendation_name,
        )
    ) if assessment.recommendation_name else None
    flags = evaluate_red_flags(db, assessment.opportunity_id)
    actions = db.scalars(select(ActionItem).where(ActionItem.assessment_id == assessment.id)).all()
    users = {row.id: row.full_name for row in db.scalars(select(User)).all()}
    return {
        "id": str(assessment.id),
        "assessment_number": assessment.assessment_number,
        "opportunity_id": str(assessment.opportunity_id),
        "opportunity_name": opportunity.name,
        "opportunity_reference": opportunity.reference_number,
        "status": assessment.status,
        "completion_percentage": float(display_score(assessment.completion_percentage or 0)),
        "calculated_score": _float(display_score(assessment.calculated_score)) if assessment.calculated_score is not None else None,
        "calculated_score_exact": format(to_decimal(assessment.calculated_score), "f") if assessment.calculated_score is not None else None,
        "scores_complete": assessment.scores_complete,
        "recommendation_name": assessment.recommendation_name,
        "recommendation_final": assessment.recommendation_final,
        "recommendation_description": rule.description if rule else "",
        "recommendation_action": rule.management_action if rule else "",
        "recommendation_color": rule.color if rule else "#1B4F8A",
        "recommendation_options": [
            item.recommendation_name
            for item in db.scalars(
                select(RecommendationRule)
                .where(RecommendationRule.template_version_id == version.id)
                .order_by(RecommendationRule.priority, RecommendationRule.minimum_score.desc())
            ).all()
        ],
        "decision_options": codes(db, "decision"),
        "template": {
            "id": str(template.id),
            "name": template.name,
            "version_id": str(version.id),
            "version_number": version.version_number,
            "version_status": version.status,
        },
        "scale": scale,
        "criteria": criteria_out,
        "questions": [
            {
                "id": str(question.id),
                "prompt": question.prompt,
                "question_type": question.question_type,
                "is_mandatory": question.is_mandatory,
                "options": question.options or [],
                "criterion_id": str(question.criterion_id) if question.criterion_id else None,
                "response_text": responses[question.id].response_text if question.id in responses else "",
                "response_json": responses[question.id].response_json if question.id in responses else None,
            }
            for question in questions
            if question.is_active
        ],
        "evidence": [
            {
                "id": str(item.id),
                "criterion_id": str(item.criterion_id) if item.criterion_id else None,
                "file_name": item.file_name,
                "uploaded_at": item.uploaded_at.isoformat(),
            }
            for item in evidence
        ],
        "assignments": [
            {
                "user_id": str(item.user_id),
                "user_name": users.get(item.user_id, ""),
                "criterion_id": str(item.criterion_id) if item.criterion_id else None,
            }
            for item in assignments
        ],
        "gaps": gaps,
        "strengths": strengths,
        "red_flags": flags,
        "submitted_red_flags": assessment.submitted_red_flags or [],
        "blockers": blocking_reasons(db, assessment) if assessment.status in EDITABLE_ASSESSMENT_STATUSES else [],
        "actions": [
            {
                "id": str(action.id),
                "reference_number": action.reference_number,
                "title": action.title,
                "status": action.status,
                "priority": action.priority,
                "is_mandatory_for_commitment": action.is_mandatory_for_commitment,
            }
            for action in actions
        ],
        "can_edit": can_score(db, user, assessment, None) or any(
            can_score(db, user, assessment, _uuid(criterion["id"])) for criterion in criteria_out
        ),
        "parent_assessment_id": str(assessment.parent_assessment_id) if assessment.parent_assessment_id else None,
    }


def _ensure_gap_actions(db: Session, assessment: Assessment, user: User) -> None:
    report = present_assessment(db, user, assessment)
    for gap in report["gaps"]:
        existing = db.scalar(
            select(ActionItem).where(
                ActionItem.assessment_id == assessment.id,
                ActionItem.criterion_id == _uuid(gap["criterion_id"]),
                ActionItem.status != "cancelled",
            )
        )
        if existing:
            continue
        db.add(
            ActionItem(
                reference_number=next_reference(db, "ACT", ActionItem, "reference_number"),
                opportunity_id=assessment.opportunity_id,
                assessment_id=assessment.id,
                criterion_id=_uuid(gap["criterion_id"]),
                title=f"Close gap: {gap['criterion_name']}",
                identified_gap=gap["summary"],
                description=gap["suggestion"],
                priority="high" if gap["severity"] == "weak" else "medium",
                status="not_started",
                owner_id=db.get(Opportunity, assessment.opportunity_id).owner_id,
            )
        )


def _criterion_row(db: Session, assessment_id, criterion_id) -> CriterionScore:
    row = db.scalar(
        select(CriterionScore).where(CriterionScore.assessment_id == assessment_id, CriterionScore.criterion_id == criterion_id)
    )
    if row is None:
        row = CriterionScore(assessment_id=assessment_id, criterion_id=criterion_id, comments="", gaps="")
        db.add(row)
        db.flush()
    return row


def _sub_row(db: Session, assessment_id, subcriterion_id) -> SubcriterionScore:
    row = db.scalar(
        select(SubcriterionScore).where(
            SubcriterionScore.assessment_id == assessment_id,
            SubcriterionScore.subcriterion_id == subcriterion_id,
        )
    )
    if row is None:
        row = SubcriterionScore(assessment_id=assessment_id, subcriterion_id=subcriterion_id, comments="")
        db.add(row)
        db.flush()
    return row


def _validate_choice(db: Session, assessment: Assessment, selected) -> None:
    if selected is None:
        return
    scale = db.scalar(
        select(ScoringScale)
        .where(ScoringScale.template_version_id == assessment.template_version_id)
        .options(selectinload(ScoringScale.values))
    )
    if _match_scale_value(scale.values, selected) is None:
        fail(400, "Select a rating from the configured scoring scale")


def _match_scale_value(values: list[ScoringScaleValue], selected):
    target = to_decimal(selected).quantize(Decimal("0.01"))
    for value in values:
        if value.is_selectable and to_decimal(value.numeric_value).quantize(Decimal("0.01")) == target:
            return value
    return None


def _needs_justification(scale, selected) -> bool:
    if scale is None:
        return False
    value = _match_scale_value(scale.values, selected)
    return bool(value and value.requires_justification)


def _uuid(value):
    import uuid

    return value if not isinstance(value, str) else uuid.UUID(value)


def _float(value):
    if value is None:
        return None
    return float(value)
