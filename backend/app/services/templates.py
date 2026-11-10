from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.tables import (
    Assessment,
    AssessmentQuestion,
    AssessmentTemplate,
    AssessmentTemplateVersion,
    EvaluationCriterion,
    EvaluationSubcriterion,
    RecommendationRule,
    ScoringScale,
    ScoringScaleValue,
    utcnow,
)
from app.services.access import fail
from app.services.constants import DEFAULT_RULES, DEFAULT_SCALE
from app.services.recommendation import RecommendationBand, RecommendationConfigError, validate_bands
from app.services.records import audit
from app.services.scoring import to_decimal
from app.services.weights import WeightValidationError, validate_weight_total


def list_templates(db: Session) -> list[AssessmentTemplate]:
    return db.scalars(select(AssessmentTemplate).order_by(AssessmentTemplate.name)).all()


def get_template(db: Session, template_id) -> AssessmentTemplate:
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        fail(404, "Assessment template was not found")
    return template


def versions_for(db: Session, template_id) -> list[AssessmentTemplateVersion]:
    return db.scalars(
        select(AssessmentTemplateVersion)
        .where(AssessmentTemplateVersion.template_id == template_id)
        .order_by(AssessmentTemplateVersion.version_number)
    ).all()


def draft_version(versions: list[AssessmentTemplateVersion]) -> AssessmentTemplateVersion | None:
    return next((version for version in versions if version.status == "draft"), None)


def published_version(db: Session, template: AssessmentTemplate) -> AssessmentTemplateVersion | None:
    if not template.current_version_id:
        return None
    version = db.get(AssessmentTemplateVersion, template.current_version_id)
    if version and version.status == "published":
        return version
    return db.scalar(
        select(AssessmentTemplateVersion)
        .where(
            AssessmentTemplateVersion.template_id == template.id,
            AssessmentTemplateVersion.status == "published",
        )
        .order_by(AssessmentTemplateVersion.version_number.desc())
    )


def create_template(db: Session, user, name: str, description: str, template_type: str) -> AssessmentTemplate:
    existing = db.scalar(select(AssessmentTemplate).where(func.lower(AssessmentTemplate.name) == name.strip().lower()))
    if existing:
        fail(409, "An assessment template with this name already exists")
    template = AssessmentTemplate(
        name=name.strip(),
        description=description.strip(),
        template_type=template_type.strip() or "opportunity",
        status="draft",
        created_by=user.id,
    )
    db.add(template)
    db.flush()
    version = AssessmentTemplateVersion(
        template_id=template.id,
        version_number=1,
        status="draft",
        gap_normalized_threshold=Decimal("0.6000"),
    )
    db.add(version)
    db.flush()
    _write_scale(db, version, _default_scale_payload())
    _write_rules(db, version, _default_rule_payload())
    template.current_version_id = version.id
    audit(db, user_id=user.id, entity_type="template", entity_id=template.id, action="template.created", new={"name": template.name})
    return template


def update_draft(db: Session, user, template_id, payload) -> AssessmentTemplateVersion:
    template = get_template(db, template_id)
    version = draft_version(versions_for(db, template.id))
    if version is None:
        fail(409, "Published templates are immutable. Create a new version before editing.")
    if db.scalar(select(func.count()).select_from(Assessment).where(Assessment.template_version_id == version.id)):
        fail(409, "This version is already used by an assessment and cannot be edited")
    if payload.name is not None:
        template.name = payload.name.strip()
    if payload.description is not None:
        template.description = payload.description.strip()
    if payload.template_type is not None:
        template.template_type = payload.template_type.strip()
    if payload.gap_normalized_threshold is not None:
        threshold = to_decimal(payload.gap_normalized_threshold)
        if threshold < 0 or threshold > 1:
            fail(400, "Gap threshold must be between 0 and 1")
        version.gap_normalized_threshold = threshold
    if payload.criteria is not None:
        _replace_criteria(db, version, payload.criteria)
    if payload.scale is not None:
        _write_scale(db, version, payload.scale)
    if payload.recommendation_rules is not None:
        _write_rules(db, version, payload.recommendation_rules)
    if payload.questions is not None:
        _write_questions(db, version, payload.questions)
    db.flush()
    audit(
        db,
        user_id=user.id,
        entity_type="template",
        entity_id=template.id,
        action="template.updated",
        new={"version": version.version_number},
    )
    return version


def publish(db: Session, user, template_id) -> AssessmentTemplateVersion:
    template = get_template(db, template_id)
    version = draft_version(versions_for(db, template.id))
    if version is None:
        fail(409, "There is no draft version to publish")
    errors = validate_version(db, version)
    if errors:
        fail(400, " ".join(errors))
    for existing in versions_for(db, template.id):
        if existing.status == "published":
            existing.status = "superseded"
    version.status = "published"
    version.published_at = utcnow()
    version.effective_from = date.today()
    template.current_version_id = version.id
    template.status = "active"
    audit(
        db,
        user_id=user.id,
        entity_type="template",
        entity_id=template.id,
        action="template.published",
        new={"version": version.version_number, "version_id": str(version.id)},
    )
    return version


def start_new_version(db: Session, user, template_id) -> AssessmentTemplateVersion:
    template = get_template(db, template_id)
    versions = versions_for(db, template.id)
    existing_draft = draft_version(versions)
    if existing_draft:
        return existing_draft
    source = published_version(db, template)
    if source is None:
        fail(409, "Publish the first version before creating another")
    version = AssessmentTemplateVersion(
        template_id=template.id,
        version_number=max(item.version_number for item in versions) + 1,
        status="draft",
        gap_normalized_threshold=source.gap_normalized_threshold,
    )
    db.add(version)
    db.flush()
    _copy_version_content(db, source, version)
    audit(
        db,
        user_id=user.id,
        entity_type="template",
        entity_id=template.id,
        action="template.versioned",
        new={"version": version.version_number, "copied_from": str(source.id)},
    )
    return version


def validate_version(db: Session, version: AssessmentTemplateVersion) -> list[str]:
    db.flush()
    errors: list[str] = []
    criteria = _criteria(db, version.id)
    active = [criterion for criterion in criteria if criterion.is_active]
    try:
        validate_weight_total([criterion.weight for criterion in active], "Active criterion weights")
    except WeightValidationError as exc:
        errors.append(str(exc))
    for criterion in active:
        subs = [sub for sub in criterion.subcriteria if sub.is_active]
        if not subs:
            continue
        try:
            validate_weight_total([sub.weight for sub in subs], f"{criterion.name} subcriterion weights")
        except WeightValidationError as exc:
            errors.append(str(exc))
    scale = _scale(db, version.id)
    if scale is None or scale.maximum_value is None or to_decimal(scale.maximum_value) <= 0:
        errors.append("A scoring scale with a maximum above zero is required.")
    elif not any(value.is_selectable for value in scale.values):
        errors.append("The scoring scale needs at least one selectable rating.")
    try:
        validate_bands(_bands(db, version.id))
    except RecommendationConfigError as exc:
        errors.append(str(exc))
    return errors


def present_template(db: Session, template: AssessmentTemplate) -> dict:
    versions = versions_for(db, template.id)
    draft = draft_version(versions)
    current = db.get(AssessmentTemplateVersion, template.current_version_id) if template.current_version_id else None
    return {
        "id": str(template.id),
        "name": template.name,
        "description": template.description,
        "template_type": template.template_type,
        "status": template.status,
        "current_version_id": str(template.current_version_id) if template.current_version_id else None,
        "versions": [
            {
                "id": str(version.id),
                "version_number": version.version_number,
                "status": version.status,
                "published_at": version.published_at.isoformat() if version.published_at else None,
            }
            for version in versions
        ],
        "draft": present_version(db, draft) if draft else None,
        "published": present_version(db, current) if current and current.status == "published" else None,
    }


def present_version(db: Session, version: AssessmentTemplateVersion | None) -> dict | None:
    if version is None:
        return None
    criteria = _criteria(db, version.id)
    scale = _scale(db, version.id)
    rules = db.scalars(
        select(RecommendationRule)
        .where(RecommendationRule.template_version_id == version.id)
        .order_by(RecommendationRule.priority, RecommendationRule.minimum_score)
    ).all()
    questions = db.scalars(
        select(AssessmentQuestion)
        .where(AssessmentQuestion.template_version_id == version.id)
        .order_by(AssessmentQuestion.display_order)
    ).all()
    criterion_index = {criterion.id: index for index, criterion in enumerate(criteria)}
    return {
        "id": str(version.id),
        "version_number": version.version_number,
        "status": version.status,
        "gap_normalized_threshold": float(version.gap_normalized_threshold),
        "criteria": [
            {
                "id": str(criterion.id),
                "name": criterion.name,
                "description": criterion.description,
                "weight": float(criterion.weight),
                "is_mandatory": criterion.is_mandatory,
                "is_active": criterion.is_active,
                "requires_evidence": criterion.requires_evidence,
                "subcriteria": [
                    {
                        "id": str(sub.id),
                        "name": sub.name,
                        "description": sub.description,
                        "weight": float(sub.weight),
                        "is_mandatory": sub.is_mandatory,
                        "is_active": sub.is_active,
                        "scoring_guidance": sub.scoring_guidance,
                    }
                    for sub in sorted(criterion.subcriteria, key=lambda item: item.display_order)
                ],
            }
            for criterion in criteria
        ],
        "scale": None
        if scale is None
        else {
            "name": scale.name,
            "minimum_value": float(scale.minimum_value),
            "maximum_value": float(scale.maximum_value),
            "values": [
                {
                    "numeric_value": float(value.numeric_value),
                    "label": value.label,
                    "description": value.description,
                    "is_selectable": value.is_selectable,
                    "requires_justification": value.requires_justification,
                    "is_weak": value.is_weak,
                }
                for value in sorted(scale.values, key=lambda item: item.display_order, reverse=True)
            ],
        },
        "recommendation_rules": [
            {
                "recommendation_name": rule.recommendation_name,
                "minimum_score": float(rule.minimum_score),
                "maximum_score": float(rule.maximum_score),
                "description": rule.description,
                "management_action": rule.management_action,
                "color": rule.color,
                "priority": rule.priority,
            }
            for rule in rules
        ],
        "questions": [
            {
                "prompt": question.prompt,
                "question_type": question.question_type,
                "is_mandatory": question.is_mandatory,
                "is_active": question.is_active,
                "options": question.options or [],
                "criterion_index": criterion_index.get(question.criterion_id),
            }
            for question in questions
        ],
        "validation_errors": validate_version(db, version) if version.status == "draft" else [],
    }


def _criteria(db: Session, version_id) -> list[EvaluationCriterion]:
    return db.scalars(
        select(EvaluationCriterion)
        .where(EvaluationCriterion.template_version_id == version_id)
        .options(selectinload(EvaluationCriterion.subcriteria))
        .order_by(EvaluationCriterion.display_order)
    ).all()


def _scale(db: Session, version_id) -> ScoringScale | None:
    return db.scalar(
        select(ScoringScale)
        .where(ScoringScale.template_version_id == version_id)
        .options(selectinload(ScoringScale.values))
    )


def _bands(db: Session, version_id) -> list[RecommendationBand]:
    rules = db.scalars(select(RecommendationRule).where(RecommendationRule.template_version_id == version_id)).all()
    return [
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
    ]


def _replace_criteria(db: Session, version: AssessmentTemplateVersion, criteria) -> None:
    existing_ids = db.scalars(select(EvaluationCriterion.id).where(EvaluationCriterion.template_version_id == version.id)).all()
    if existing_ids:
        db.execute(delete(EvaluationSubcriterion).where(EvaluationSubcriterion.criterion_id.in_(existing_ids)))
        db.execute(delete(EvaluationCriterion).where(EvaluationCriterion.template_version_id == version.id))
        db.flush()
    for index, item in enumerate(criteria):
        criterion = EvaluationCriterion(
            template_version_id=version.id,
            name=item.name.strip(),
            description=(item.description or "").strip(),
            weight=to_decimal(item.weight),
            display_order=index,
            is_mandatory=item.is_mandatory,
            is_active=item.is_active,
            requires_evidence=item.requires_evidence,
        )
        db.add(criterion)
        db.flush()
        for sub_index, sub in enumerate(item.subcriteria):
            db.add(
                EvaluationSubcriterion(
                    criterion_id=criterion.id,
                    name=sub.name.strip(),
                    description=(sub.description or "").strip(),
                    weight=to_decimal(sub.weight),
                    display_order=sub_index,
                    is_mandatory=sub.is_mandatory,
                    is_active=sub.is_active,
                    scoring_guidance=(sub.scoring_guidance or "").strip(),
                )
            )


def _write_scale(db: Session, version: AssessmentTemplateVersion, scale) -> None:
    current = _scale(db, version.id)
    if current:
        db.execute(delete(ScoringScaleValue).where(ScoringScaleValue.scoring_scale_id == current.id))
        db.expire(current, ["values"])
        db.delete(current)
        db.flush()
    data = scale if isinstance(scale, dict) else scale
    name = data["name"] if isinstance(data, dict) else data.name
    minimum = data["minimum_value"] if isinstance(data, dict) else data.minimum_value
    maximum = data["maximum_value"] if isinstance(data, dict) else data.maximum_value
    values = data["values"] if isinstance(data, dict) else data.values
    row = ScoringScale(
        template_version_id=version.id,
        name=name,
        minimum_value=to_decimal(minimum),
        maximum_value=to_decimal(maximum),
    )
    db.add(row)
    db.flush()
    for index, value in enumerate(values):
        numeric = value["numeric_value"] if isinstance(value, dict) else value.numeric_value
        db.add(
            ScoringScaleValue(
                scoring_scale_id=row.id,
                numeric_value=to_decimal(numeric),
                label=value["label"] if isinstance(value, dict) else value.label,
                description=(value["description"] if isinstance(value, dict) else value.description) or "",
                display_order=len(values) - index,
                is_selectable=value["is_selectable"] if isinstance(value, dict) else value.is_selectable,
                requires_justification=value["requires_justification"] if isinstance(value, dict) else value.requires_justification,
                is_weak=value["is_weak"] if isinstance(value, dict) else value.is_weak,
            )
        )


def _write_rules(db: Session, version: AssessmentTemplateVersion, rules) -> None:
    db.execute(delete(RecommendationRule).where(RecommendationRule.template_version_id == version.id))
    db.flush()
    for index, rule in enumerate(rules):
        is_dict = isinstance(rule, dict)
        db.add(
            RecommendationRule(
                template_version_id=version.id,
                recommendation_name=(rule["recommendation_name"] if is_dict else rule.recommendation_name).strip(),
                minimum_score=to_decimal(rule["minimum_score"] if is_dict else rule.minimum_score),
                maximum_score=to_decimal(rule["maximum_score"] if is_dict else rule.maximum_score),
                description=(rule["description"] if is_dict else rule.description) or "",
                management_action=(rule["management_action"] if is_dict else rule.management_action) or "",
                color=(rule["color"] if is_dict else rule.color) or "#1B4F8A",
                priority=rule["priority"] if is_dict else (rule.priority or index + 1),
            )
        )


def _write_questions(db: Session, version: AssessmentTemplateVersion, questions) -> None:
    criteria = _criteria(db, version.id)
    db.execute(delete(AssessmentQuestion).where(AssessmentQuestion.template_version_id == version.id))
    db.flush()
    for index, question in enumerate(questions):
        criterion_id = None
        criterion_index = question.criterion_index
        if criterion_index is not None:
            if criterion_index < 0 or criterion_index >= len(criteria):
                fail(400, "A question refers to a criterion that does not exist")
            criterion_id = criteria[criterion_index].id
        db.add(
            AssessmentQuestion(
                template_version_id=version.id,
                criterion_id=criterion_id,
                prompt=question.prompt.strip(),
                question_type=question.question_type,
                is_mandatory=question.is_mandatory,
                is_active=question.is_active,
                options=question.options or None,
                display_order=index,
            )
        )


def _copy_version_content(db: Session, source: AssessmentTemplateVersion, target: AssessmentTemplateVersion) -> None:
    id_map: dict = {}
    for criterion in _criteria(db, source.id):
        copied = EvaluationCriterion(
            template_version_id=target.id,
            name=criterion.name,
            description=criterion.description,
            weight=criterion.weight,
            display_order=criterion.display_order,
            is_mandatory=criterion.is_mandatory,
            is_active=criterion.is_active,
            requires_evidence=criterion.requires_evidence,
        )
        db.add(copied)
        db.flush()
        id_map[criterion.id] = copied.id
        for sub in sorted(criterion.subcriteria, key=lambda item: item.display_order):
            copied_sub = EvaluationSubcriterion(
                criterion_id=copied.id,
                name=sub.name,
                description=sub.description,
                weight=sub.weight,
                display_order=sub.display_order,
                is_mandatory=sub.is_mandatory,
                is_active=sub.is_active,
                scoring_guidance=sub.scoring_guidance,
            )
            db.add(copied_sub)
            db.flush()
            id_map[sub.id] = copied_sub.id
    scale = _scale(db, source.id)
    if scale:
        _write_scale(
            db,
            target,
            {
                "name": scale.name,
                "minimum_value": scale.minimum_value,
                "maximum_value": scale.maximum_value,
                "values": [
                    {
                        "numeric_value": value.numeric_value,
                        "label": value.label,
                        "description": value.description,
                        "is_selectable": value.is_selectable,
                        "requires_justification": value.requires_justification,
                        "is_weak": value.is_weak,
                    }
                    for value in sorted(scale.values, key=lambda item: item.numeric_value, reverse=True)
                ],
            },
        )
    rules = db.scalars(select(RecommendationRule).where(RecommendationRule.template_version_id == source.id)).all()
    _write_rules(
        db,
        target,
        [
            {
                "recommendation_name": rule.recommendation_name,
                "minimum_score": rule.minimum_score,
                "maximum_score": rule.maximum_score,
                "description": rule.description,
                "management_action": rule.management_action,
                "color": rule.color,
                "priority": rule.priority,
            }
            for rule in rules
        ],
    )
    questions = db.scalars(
        select(AssessmentQuestion).where(AssessmentQuestion.template_version_id == source.id).order_by(AssessmentQuestion.display_order)
    ).all()
    criteria = _criteria(db, target.id)
    index_by_id = {criterion.id: index for index, criterion in enumerate(criteria)}
    copied_questions = []
    for question in questions:
        mapped = id_map.get(question.criterion_id)
        copied_questions.append(
            type("Q", (), {
                "prompt": question.prompt,
                "question_type": question.question_type,
                "is_mandatory": question.is_mandatory,
                "is_active": question.is_active,
                "options": question.options,
                "criterion_index": index_by_id.get(mapped),
            })()
        )
    _write_questions(db, target, copied_questions)


def _default_scale_payload() -> dict:
    return {
        "name": "Five-level qualitative scale",
        "minimum_value": 1,
        "maximum_value": 5,
        "values": [
            {
                "numeric_value": numeric,
                "label": label,
                "description": description,
                "is_selectable": True,
                "requires_justification": requires_justification,
                "is_weak": is_weak,
            }
            for numeric, label, description, requires_justification, is_weak in DEFAULT_SCALE
        ],
    }


def _default_rule_payload() -> list[dict]:
    return [
        {
            "recommendation_name": name,
            "minimum_score": minimum,
            "maximum_score": maximum,
            "description": description,
            "management_action": action,
            "color": color,
            "priority": priority,
        }
        for name, minimum, maximum, description, action, color, priority in DEFAULT_RULES
    ]


def install_standard_template(db: Session, user) -> AssessmentTemplate:
    """Create and publish the initial seven-criterion methodology."""
    from app.services.constants import DEFAULT_CRITERIA

    template = create_template(
        db,
        user,
        "Standard Opportunity Assessment",
        "Diyar's default methodology for qualifying a business opportunity before commitment.",
        "opportunity",
    )
    version = draft_version(versions_for(db, template.id))
    criteria_payload = []
    for name, description, weight, subs in DEFAULT_CRITERIA:
        criteria_payload.append(
            type("C", (), {
                "name": name,
                "description": description,
                "weight": Decimal(str(weight)),
                "is_mandatory": True,
                "is_active": True,
                "requires_evidence": False,
                "subcriteria": [
                    type("S", (), {
                        "name": sub_name,
                        "description": "",
                        "weight": Decimal(str(sub_weight)),
                        "is_mandatory": True,
                        "is_active": True,
                        "scoring_guidance": guidance,
                    })()
                    for sub_name, sub_weight, guidance in subs
                ],
            })()
        )
    questions = [
        type("Q", (), {
            "prompt": "Describe the strategic rationale for pursuing this opportunity.",
            "question_type": "long_text",
            "is_mandatory": True,
            "is_active": True,
            "options": None,
            "criterion_index": 0,
        })(),
        type("Q", (), {
            "prompt": "Summarise the delivery assumptions that the technical score depends on.",
            "question_type": "long_text",
            "is_mandatory": True,
            "is_active": True,
            "options": None,
            "criterion_index": 2,
        })(),
    ]
    payload = type("P", (), {
        "name": None,
        "description": None,
        "template_type": None,
        "gap_normalized_threshold": None,
        "criteria": criteria_payload,
        "scale": None,
        "recommendation_rules": None,
        "questions": questions,
    })()
    update_draft(db, user, template.id, payload)
    publish(db, user, template.id)
    return template
