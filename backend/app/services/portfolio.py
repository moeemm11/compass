from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.tables import (
    ActionItem,
    ApprovalRecord,
    Assessment,
    AssessmentTemplate,
    Attachment,
    AuditLog,
    BusinessUnit,
    CommercialAssessment,
    Country,
    Currency,
    ManagementDecision,
    Opportunity,
    OpportunityPartner,
    OpportunityServiceLine,
    Partner,
    PartnerCapability,
    PartnerCapabilityMapping,
    ResourceRequirement,
    Risk,
    Sector,
    ServiceLine,
    User,
    utcnow,
)
from app.services.access import fail, has_permission
from app.services.assessments import can_edit_opportunity, can_view_opportunity
from app.services.constants import (
    ACTION_PRIORITIES,
    ACTION_STATUSES,
    AVAILABILITY_STATUSES,
    COMMITMENT_STATUSES,
    MANUAL_TRANSITIONS,
    OPPORTUNITY_SOURCES,
    RESOURCE_TYPES,
    RISK_CATEGORIES,
    RISK_STATUSES,
    STRATEGIC_IMPORTANCE,
)
from app.services.financials import CommercialInputs, calculate_commercial
from app.services.records import ACTION_SUMMARIES, audit, next_reference, status_label
from app.services.scoring import display_score, to_decimal


def create_opportunity(db: Session, user: User, payload) -> Opportunity:
    if not has_permission(user, "opportunities.create", db):
        fail(403, "You do not have permission to register an opportunity")
    _validate_opportunity_refs(db, payload)
    owner = db.get(User, payload.owner_id)
    if owner is None or not owner.is_active:
        fail(400, "Choose an active business development owner")
    opportunity = Opportunity(
        reference_number=next_reference(db, "OPP", Opportunity, "reference_number"),
        name=payload.name.strip(),
        client_name=payload.client_name.strip(),
        country_id=payload.country_id,
        sector_id=payload.sector_id,
        business_unit_id=payload.business_unit_id,
        description=payload.description.strip(),
        opportunity_source=payload.opportunity_source,
        estimated_value=payload.estimated_value,
        currency_code=payload.currency_code,
        expected_award_date=payload.expected_award_date,
        expected_start_date=payload.expected_start_date,
        expected_duration=payload.expected_duration,
        owner_id=payload.owner_id,
        status="identified",
        strategic_importance=payload.strategic_importance,
        partner_required=payload.partner_required,
    )
    db.add(opportunity)
    db.flush()
    _set_service_lines(db, opportunity, payload.service_line_ids)
    audit(
        db,
        user_id=user.id,
        entity_type="opportunity",
        entity_id=opportunity.id,
        action="opportunity.created",
        opportunity_id=opportunity.id,
        new={"name": opportunity.name, "reference": opportunity.reference_number},
    )
    return opportunity


def update_opportunity(db: Session, user: User, opportunity: Opportunity, payload) -> Opportunity:
    if not can_edit_opportunity(db, user, opportunity):
        fail(403, "You can only edit opportunities you own")
    data = payload.model_dump(exclude_unset=True)
    if "service_line_ids" in data:
        if not data["service_line_ids"]:
            fail(400, "Select at least one service line")
        _set_service_lines(db, opportunity, data.pop("service_line_ids"))
    if "opportunity_source" in data and data["opportunity_source"] not in OPPORTUNITY_SOURCES:
        fail(400, "Opportunity source is not recognised")
    if "strategic_importance" in data and data["strategic_importance"] not in STRATEGIC_IMPORTANCE + [None]:
        fail(400, "Strategic importance is not recognised")
    if "currency_code" in data and db.get(Currency, data["currency_code"]) is None:
        fail(400, "Currency is not recognised")
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(opportunity, field, value)
    audit(
        db,
        user_id=user.id,
        entity_type="opportunity",
        entity_id=opportunity.id,
        action="opportunity.updated",
        opportunity_id=opportunity.id,
        new=payload.model_dump(exclude_unset=True, mode="json"),
    )
    return opportunity


def transition_opportunity(db: Session, user: User, opportunity: Opportunity, target: str) -> Opportunity:
    if not can_edit_opportunity(db, user, opportunity):
        fail(403, "You can only change the status of opportunities you own")
    allowed = MANUAL_TRANSITIONS.get(opportunity.status, set())
    if target not in allowed:
        fail(400, f"Cannot move an opportunity from {status_label(opportunity.status)} to {status_label(target)}")
    previous = opportunity.status
    opportunity.status = target
    audit(
        db,
        user_id=user.id,
        entity_type="opportunity",
        entity_id=opportunity.id,
        action="opportunity.transition",
        opportunity_id=opportunity.id,
        old={"status": previous},
        new={"status": target},
    )
    return opportunity


def archive_opportunity(db: Session, user: User, opportunity: Opportunity) -> None:
    if not can_edit_opportunity(db, user, opportunity) and not has_permission(user, "admin.full", db):
        fail(403, "You do not have permission to archive this opportunity")
    opportunity.deleted_at = utcnow()
    audit(db, user_id=user.id, entity_type="opportunity", entity_id=opportunity.id, action="opportunity.archived", opportunity_id=opportunity.id)


def visible_opportunities(db: Session, user: User):
    statement = select(Opportunity).where(Opportunity.deleted_at.is_(None)).options(
        selectinload(Opportunity.country),
        selectinload(Opportunity.sector),
        selectinload(Opportunity.business_unit),
        selectinload(Opportunity.owner),
        selectinload(Opportunity.service_lines),
    )
    if not has_permission(user, "opportunities.view_all", db):
        if not has_permission(user, "opportunities.view_assigned", db):
            fail(403, "You do not have permission to view opportunities")
        from app.models.tables import AssessmentAssignment

        assigned_ids = select(Assessment.opportunity_id).join(
            AssessmentAssignment, AssessmentAssignment.assessment_id == Assessment.id
        ).where(AssessmentAssignment.user_id == user.id)
        statement = statement.where(or_(Opportunity.owner_id == user.id, Opportunity.id.in_(assigned_ids)))
    return statement


def list_opportunities(db: Session, user: User, **filters):
    statement = visible_opportunities(db, user)
    if filters.get("search"):
        term = f"%{filters['search'].strip()}%"
        statement = statement.where(
            or_(Opportunity.name.ilike(term), Opportunity.client_name.ilike(term), Opportunity.reference_number.ilike(term))
        )
    if filters.get("status"):
        statement = statement.where(Opportunity.status == filters["status"])
    if filters.get("country_id"):
        statement = statement.where(Opportunity.country_id == filters["country_id"])
    if filters.get("business_unit_id"):
        statement = statement.where(Opportunity.business_unit_id == filters["business_unit_id"])
    if filters.get("owner_id"):
        statement = statement.where(Opportunity.owner_id == filters["owner_id"])
    if filters.get("service_line_id"):
        statement = statement.where(
            Opportunity.id.in_(
                select(OpportunityServiceLine.opportunity_id).where(
                    OpportunityServiceLine.service_line_id == filters["service_line_id"]
                )
            )
        )
    rows = db.scalars(statement.order_by(Opportunity.updated_at.desc())).all()
    latest = _latest_assessments(db, [row.id for row in rows])
    partner_names = _partner_names(db, [row.id for row in rows])
    filtered = []
    for row in rows:
        assessment = latest.get(row.id)
        if filters.get("recommendation") and (assessment is None or assessment.recommendation_name != filters["recommendation"]):
            continue
        if filters.get("partner_id") and filters["partner_id"] not in partner_names.get(row.id, {}):
            continue
        if filters.get("date_from") and row.created_at.date() < filters["date_from"]:
            continue
        if filters.get("date_to") and row.created_at.date() > filters["date_to"]:
            continue
        filtered.append(row)
    page = max(filters.get("page") or 1, 1)
    page_size = min(max(filters.get("page_size") or 20, 1), 100)
    start = (page - 1) * page_size
    sliced = filtered[start : start + page_size]
    return {
        "items": [present_opportunity(db, row, latest.get(row.id)) for row in sliced],
        "total": len(filtered),
        "page": page,
        "page_size": page_size,
    }


def present_opportunity(db: Session, opportunity: Opportunity, assessment: Assessment | None = None, detailed: bool = False) -> dict:
    if assessment is None and detailed:
        assessment = _latest_assessments(db, [opportunity.id]).get(opportunity.id)
    payload = {
        "id": str(opportunity.id),
        "reference_number": opportunity.reference_number,
        "name": opportunity.name,
        "client_name": opportunity.client_name,
        "country": {"id": str(opportunity.country_id), "name": opportunity.country.name if opportunity.country else ""},
        "sector": {"id": str(opportunity.sector_id), "name": opportunity.sector.name if opportunity.sector else ""},
        "business_unit": None
        if opportunity.business_unit_id is None
        else {"id": str(opportunity.business_unit_id), "name": opportunity.business_unit.name if opportunity.business_unit else ""},
        "description": opportunity.description,
        "opportunity_source": opportunity.opportunity_source,
        "estimated_value": _money(opportunity.estimated_value),
        "currency_code": opportunity.currency_code,
        "expected_award_date": _date(opportunity.expected_award_date),
        "expected_start_date": _date(opportunity.expected_start_date),
        "expected_duration": opportunity.expected_duration,
        "owner": {"id": str(opportunity.owner_id), "full_name": opportunity.owner.full_name if opportunity.owner else ""},
        "status": opportunity.status,
        "status_label": status_label(opportunity.status),
        "strategic_importance": opportunity.strategic_importance,
        "partner_required": opportunity.partner_required,
        "service_lines": [{"id": str(line.id), "name": line.name} for line in opportunity.service_lines],
        "score": _money(display_score(assessment.calculated_score)) if assessment and assessment.calculated_score is not None else None,
        "recommendation": assessment.recommendation_name if assessment else None,
        "assessment_status": assessment.status if assessment else None,
        "created_at": opportunity.created_at.isoformat() if opportunity.created_at else None,
        "updated_at": opportunity.updated_at.isoformat() if opportunity.updated_at else None,
    }
    if not detailed:
        return payload
    payload["assessments"] = [
        {
            "id": str(item.id),
            "assessment_number": item.assessment_number,
            "status": item.status,
            "calculated_score": _money(display_score(item.calculated_score)) if item.calculated_score is not None else None,
            "recommendation_name": item.recommendation_name,
            "template_version_id": str(item.template_version_id),
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in db.scalars(select(Assessment).where(Assessment.opportunity_id == opportunity.id).order_by(Assessment.created_at.desc())).all()
    ]
    payload["risks"] = [present_risk(risk) for risk in _risks(db, opportunity.id)]
    payload["heatmap"] = heatmap(payload["risks"])
    commercial = _commercial(db, opportunity.id)
    payload["commercial"] = present_commercial(commercial) if commercial else None
    payload["partners"] = _opportunity_partners(db, opportunity.id)
    resources = db.scalars(select(ResourceRequirement).where(ResourceRequirement.opportunity_id == opportunity.id)).all()
    payload["resources"] = [present_resource(item) for item in resources]
    payload["resource_summary"] = resource_summary(resources)
    payload["actions"] = [present_action(item) for item in db.scalars(select(ActionItem).where(ActionItem.opportunity_id == opportunity.id)).all()]
    payload["decisions"] = [_decision(item, db) for item in db.scalars(select(ManagementDecision).where(ManagementDecision.opportunity_id == opportunity.id).order_by(ManagementDecision.decision_date.desc())).all()]
    payload["approvals"] = [_approval(item, db) for item in db.scalars(select(ApprovalRecord).where(ApprovalRecord.opportunity_id == opportunity.id).order_by(ApprovalRecord.decided_at)).all()]
    payload["attachments"] = _attachments(db, "opportunity", opportunity.id)
    payload["activity"] = activity(db, opportunity.id)
    payload["allowed_transitions"] = sorted(MANUAL_TRANSITIONS.get(opportunity.status, set()))
    return payload


def save_commercial(db: Session, user: User, opportunity: Opportunity, payload) -> CommercialAssessment:
    if not (
        can_edit_opportunity(db, user, opportunity)
        or has_permission(user, "commercial.edit", db)
    ):
        fail(403, "You do not have permission to edit the commercial assessment")
    if payload.currency_code != opportunity.currency_code:
        fail(400, "Commercial currency must match the opportunity currency. Currency conversion is not enabled.")
    for value in [
        payload.contract_value,
        payload.internal_cost,
        payload.partner_cost,
        payload.travel_cost,
        payload.third_party_cost,
        payload.licensing_cost,
        payload.other_cost,
        payload.bid_cost,
        payload.contingency,
    ]:
        if to_decimal(value) < 0:
            fail(400, "Commercial amounts cannot be negative")
    result = calculate_commercial(
        CommercialInputs(
            contract_value=to_decimal(payload.contract_value),
            internal_cost=to_decimal(payload.internal_cost),
            partner_cost=to_decimal(payload.partner_cost),
            travel_cost=to_decimal(payload.travel_cost),
            third_party_cost=to_decimal(payload.third_party_cost),
            licensing_cost=to_decimal(payload.licensing_cost),
            other_cost=to_decimal(payload.other_cost),
            contingency=to_decimal(payload.contingency),
            bid_cost=to_decimal(payload.bid_cost),
            probability_of_winning=to_decimal(payload.probability_of_winning),
        )
    )
    row = _commercial(db, opportunity.id)
    if row is None:
        row = CommercialAssessment(opportunity_id=opportunity.id, currency_code=payload.currency_code)
        db.add(row)
    row.assessment_id = payload.assessment_id
    row.contract_value = payload.contract_value
    row.currency_code = payload.currency_code
    row.internal_cost = payload.internal_cost
    row.partner_cost = payload.partner_cost
    row.travel_cost = payload.travel_cost
    row.third_party_cost = payload.third_party_cost
    row.licensing_cost = payload.licensing_cost
    row.other_cost = payload.other_cost
    row.bid_cost = payload.bid_cost
    row.contingency = payload.contingency
    row.probability_of_winning = payload.probability_of_winning
    row.assumptions = payload.assumptions or ""
    row.figures_confirmed = payload.figures_confirmed
    row.total_cost = result.total_cost
    row.gross_profit = result.gross_profit
    row.gross_margin = result.gross_margin
    row.expected_revenue = result.expected_revenue
    row.expected_contribution = result.expected_contribution
    row.partner_cost_percentage = result.partner_cost_percentage
    audit(db, user_id=user.id, entity_type="commercial", entity_id=opportunity.id, action="commercial.saved", opportunity_id=opportunity.id, new={"gross_margin": str(result.gross_margin)})
    db.flush()
    return row


def save_risk(db: Session, user: User, opportunity: Opportunity, payload, risk: Risk | None = None) -> Risk:
    if not can_edit_opportunity(db, user, opportunity) and not has_permission(user, "assessments.complete_any", db):
        fail(403, "You do not have permission to edit risks")
    if payload.category not in RISK_CATEGORIES:
        fail(400, "Risk category is not recognised")
    if payload.status not in RISK_STATUSES:
        fail(400, "Risk status is not recognised")
    if risk is None:
        risk = Risk(opportunity_id=opportunity.id, reference_number=next_reference(db, "RSK", Risk, "reference_number"))
        db.add(risk)
    risk.title = payload.title.strip()
    risk.description = payload.description or ""
    risk.category = payload.category
    risk.probability = payload.probability
    risk.impact = payload.impact
    risk.inherent_score = payload.probability * payload.impact
    risk.mitigation_plan = payload.mitigation_plan or ""
    risk.owner_id = payload.owner_id
    risk.target_date = payload.target_date
    risk.residual_probability = payload.residual_probability
    risk.residual_impact = payload.residual_impact
    risk.residual_score = (
        payload.residual_probability * payload.residual_impact
        if payload.residual_probability and payload.residual_impact
        else None
    )
    risk.status = payload.status
    risk.assessment_id = payload.assessment_id
    risk.criterion_id = payload.criterion_id
    risk.is_regulatory_blocker = payload.is_regulatory_blocker
    audit(db, user_id=user.id, entity_type="risk", entity_id=risk.id, action="risk.saved", opportunity_id=opportunity.id, new={"title": risk.title, "inherent_score": risk.inherent_score})
    return risk


def save_resource(db: Session, user: User, opportunity: Opportunity, payload, row: ResourceRequirement | None = None) -> ResourceRequirement:
    if not can_edit_opportunity(db, user, opportunity) and not has_permission(user, "assessments.complete_any", db):
        fail(403, "You do not have permission to edit resources")
    if payload.resource_type not in RESOURCE_TYPES or payload.availability_status not in AVAILABILITY_STATUSES:
        fail(400, "Resource type or availability is not recognised")
    if row is None:
        row = ResourceRequirement(opportunity_id=opportunity.id)
        db.add(row)
    row.role = payload.role.strip()
    row.required_skills = payload.required_skills or ""
    row.quantity = payload.quantity
    row.allocation_percentage = payload.allocation_percentage
    row.duration_months = payload.duration_months
    row.resource_type = payload.resource_type
    row.availability_status = payload.availability_status
    row.owner_id = payload.owner_id
    row.identified_gap = payload.identified_gap or payload.availability_status == "gap"
    row.notes = payload.notes or ""
    audit(db, user_id=user.id, entity_type="resource", entity_id=row.id, action="resource.saved", opportunity_id=opportunity.id, new={"role": row.role})
    return row


def save_action(db: Session, user: User, opportunity: Opportunity, payload, row: ActionItem | None = None) -> ActionItem:
    if not can_edit_opportunity(db, user, opportunity) and not has_permission(user, "assessments.complete_any", db):
        fail(403, "You do not have permission to edit actions")
    if payload.priority not in ACTION_PRIORITIES or payload.status not in ACTION_STATUSES:
        fail(400, "Action priority or status is not recognised")
    if row is None:
        row = ActionItem(opportunity_id=opportunity.id, reference_number=next_reference(db, "ACT", ActionItem, "reference_number"))
        db.add(row)
    row.assessment_id = payload.assessment_id
    row.criterion_id = payload.criterion_id
    row.title = payload.title.strip()
    row.identified_gap = payload.identified_gap or ""
    row.description = payload.description or ""
    row.owner_id = payload.owner_id
    row.priority = payload.priority
    row.due_date = payload.due_date
    row.status = payload.status
    row.completion_notes = payload.completion_notes or ""
    row.is_mandatory_for_commitment = payload.is_mandatory_for_commitment
    audit(db, user_id=user.id, entity_type="action", entity_id=row.id, action="action.saved", opportunity_id=opportunity.id, new={"title": row.title, "status": row.status})
    return row


def link_partner(db: Session, user: User, opportunity: Opportunity, payload) -> OpportunityPartner:
    if not can_edit_opportunity(db, user, opportunity):
        fail(403, "You do not have permission to link partners")
    partner = db.get(Partner, payload.partner_id)
    if partner is None or partner.deleted_at is not None:
        fail(404, "Partner was not found")
    if payload.commitment_status not in COMMITMENT_STATUSES:
        fail(400, "Commitment status is not recognised")
    row = db.scalar(
        select(OpportunityPartner).where(
            OpportunityPartner.opportunity_id == opportunity.id,
            OpportunityPartner.partner_id == partner.id,
        )
    )
    if row is None:
        row = OpportunityPartner(opportunity_id=opportunity.id, partner_id=partner.id)
        db.add(row)
    row.role = payload.role.strip()
    row.commitment_status = payload.commitment_status
    row.commercial_arrangement = payload.commercial_arrangement or ""
    audit(db, user_id=user.id, entity_type="opportunity", entity_id=opportunity.id, action="partner.linked", opportunity_id=opportunity.id, new={"partner": partner.name, "commitment": row.commitment_status})
    return row


def resource_summary(resources: list[ResourceRequirement]) -> dict:
    if not resources:
        return {
            "total_demand": 0,
            "confirmed_internal": 0,
            "external_dependency": 0,
            "critical_skill_gaps": 0,
            "delivery_feasibility": "Not assessed",
        }
    gaps = [item for item in resources if item.availability_status == "gap" or item.identified_gap]
    unconfirmed = [item for item in resources if item.availability_status == "unconfirmed"]
    partial = [item for item in resources if item.availability_status == "partial"]
    if gaps:
        feasibility = "Gaps identified"
    elif unconfirmed:
        feasibility = "Unconfirmed"
    elif partial:
        feasibility = "Feasible with constraints"
    else:
        feasibility = "Feasible"
    return {
        "total_demand": sum(item.quantity for item in resources),
        "confirmed_internal": sum(item.quantity for item in resources if item.resource_type == "internal" and item.availability_status == "available"),
        "external_dependency": sum(item.quantity for item in resources if item.resource_type == "external"),
        "critical_skill_gaps": len(gaps),
        "delivery_feasibility": feasibility,
    }


def heatmap(risks: list[dict]) -> list[dict]:
    cells = []
    for probability in range(1, 6):
        for impact in range(1, 6):
            count = sum(1 for risk in risks if risk["probability"] == probability and risk["impact"] == impact)
            cells.append({"probability": probability, "impact": impact, "count": count, "score": probability * impact})
    return cells


def activity(db: Session, opportunity_id) -> list[dict]:
    logs = db.scalars(
        select(AuditLog).where(AuditLog.opportunity_id == opportunity_id).order_by(AuditLog.created_at.desc()).limit(40)
    ).all()
    users = {row.id: row.full_name for row in db.scalars(select(User)).all()}
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "summary": ACTION_SUMMARIES.get(log.action, log.action),
            "actor": users.get(log.user_id, "System"),
            "created_at": log.created_at.isoformat(),
            "new_values": log.new_values,
        }
        for log in logs
    ]


def present_risk(risk: Risk) -> dict:
    return {
        "id": str(risk.id),
        "reference_number": risk.reference_number,
        "opportunity_id": str(risk.opportunity_id),
        "title": risk.title,
        "description": risk.description,
        "category": risk.category,
        "probability": risk.probability,
        "impact": risk.impact,
        "inherent_score": risk.inherent_score,
        "mitigation_plan": risk.mitigation_plan,
        "owner_id": str(risk.owner_id) if risk.owner_id else None,
        "target_date": _date(risk.target_date),
        "residual_probability": risk.residual_probability,
        "residual_impact": risk.residual_impact,
        "residual_score": risk.residual_score,
        "status": risk.status,
        "is_regulatory_blocker": risk.is_regulatory_blocker,
        "criterion_id": str(risk.criterion_id) if risk.criterion_id else None,
    }


def present_commercial(row: CommercialAssessment) -> dict:
    return {
        "id": str(row.id),
        "opportunity_id": str(row.opportunity_id),
        "contract_value": _money(row.contract_value),
        "currency_code": row.currency_code,
        "internal_cost": _money(row.internal_cost),
        "partner_cost": _money(row.partner_cost),
        "travel_cost": _money(row.travel_cost),
        "third_party_cost": _money(row.third_party_cost),
        "licensing_cost": _money(row.licensing_cost),
        "other_cost": _money(row.other_cost),
        "bid_cost": _money(row.bid_cost),
        "contingency": _money(row.contingency),
        "probability_of_winning": _money(row.probability_of_winning),
        "assumptions": row.assumptions,
        "figures_confirmed": row.figures_confirmed,
        "figures_label": "Confirmed commercial figures" if row.figures_confirmed else "Estimated figures. These are assumptions, not confirmed financials.",
        "total_cost": _money(row.total_cost),
        "gross_profit": _money(row.gross_profit),
        "gross_margin": _money(row.gross_margin),
        "expected_revenue": _money(row.expected_revenue),
        "expected_contribution": _money(row.expected_contribution),
        "partner_cost_percentage": _money(row.partner_cost_percentage),
    }


def present_resource(row: ResourceRequirement) -> dict:
    return {
        "id": str(row.id),
        "opportunity_id": str(row.opportunity_id),
        "role": row.role,
        "required_skills": row.required_skills,
        "quantity": row.quantity,
        "allocation_percentage": _money(row.allocation_percentage),
        "duration_months": _money(row.duration_months) if row.duration_months is not None else None,
        "resource_type": row.resource_type,
        "availability_status": row.availability_status,
        "owner_id": str(row.owner_id) if row.owner_id else None,
        "identified_gap": row.identified_gap,
        "notes": row.notes,
    }


def present_action(row: ActionItem) -> dict:
    return {
        "id": str(row.id),
        "reference_number": row.reference_number,
        "opportunity_id": str(row.opportunity_id),
        "assessment_id": str(row.assessment_id) if row.assessment_id else None,
        "criterion_id": str(row.criterion_id) if row.criterion_id else None,
        "title": row.title,
        "identified_gap": row.identified_gap,
        "description": row.description,
        "owner_id": str(row.owner_id) if row.owner_id else None,
        "priority": row.priority,
        "due_date": _date(row.due_date),
        "status": row.status,
        "completion_notes": row.completion_notes,
        "is_mandatory_for_commitment": row.is_mandatory_for_commitment,
    }


def present_partner(db: Session, partner: Partner) -> dict:
    mappings = db.scalars(select(PartnerCapabilityMapping).where(PartnerCapabilityMapping.partner_id == partner.id)).all()
    capabilities = []
    for mapping in mappings:
        capability = db.get(PartnerCapability, mapping.capability_id)
        if capability:
            capabilities.append(
                {
                    "id": str(capability.id),
                    "name": capability.name,
                    "proficiency_level": mapping.proficiency_level,
                    "evidence_reference": mapping.evidence_reference,
                }
            )
    return {
        "id": str(partner.id),
        "name": partner.name,
        "country_id": str(partner.country_id) if partner.country_id else None,
        "country_name": partner.country.name if partner.country else "",
        "description": partner.description,
        "website": partner.website,
        "contact_name": partner.contact_name,
        "contact_email": partner.contact_email,
        "contact_phone": partner.contact_phone,
        "industry": partner.industry,
        "healthcare_capabilities": partner.healthcare_capabilities,
        "technology_capabilities": partner.technology_capabilities,
        "certifications": partner.certifications,
        "project_references": partner.project_references,
        "relevant_experience": partner.relevant_experience,
        "available_consultants": partner.available_consultants,
        "partnership_status": partner.partnership_status,
        "nda_status": partner.nda_status,
        "agreement_status": partner.agreement_status,
        "commercial_arrangements": partner.commercial_arrangements,
        "relationship_owner_id": str(partner.relationship_owner_id) if partner.relationship_owner_id else None,
        "performance_history": partner.performance_history,
        "capabilities": capabilities,
    }


def _validate_opportunity_refs(db: Session, payload) -> None:
    if db.get(Country, payload.country_id) is None:
        fail(400, "Country was not found")
    if db.get(Sector, payload.sector_id) is None:
        fail(400, "Sector was not found")
    if payload.business_unit_id and db.get(BusinessUnit, payload.business_unit_id) is None:
        fail(400, "Business unit was not found")
    if db.get(Currency, payload.currency_code) is None:
        fail(400, "Currency is not recognised")
    if payload.opportunity_source not in OPPORTUNITY_SOURCES:
        fail(400, "Opportunity source is not recognised")
    if payload.strategic_importance and payload.strategic_importance not in STRATEGIC_IMPORTANCE:
        fail(400, "Strategic importance is not recognised")
    lines = db.scalars(select(ServiceLine).where(ServiceLine.id.in_(payload.service_line_ids))).all()
    if len(lines) != len(set(payload.service_line_ids)):
        fail(400, "One or more service lines were not found")


def _set_service_lines(db: Session, opportunity: Opportunity, service_line_ids) -> None:
    db.query(OpportunityServiceLine).filter(OpportunityServiceLine.opportunity_id == opportunity.id).delete()
    for service_line_id in service_line_ids:
        db.add(OpportunityServiceLine(opportunity_id=opportunity.id, service_line_id=service_line_id))
    db.flush()
    db.expire(opportunity, ["service_lines"])


def _latest_assessments(db: Session, ids) -> dict:
    if not ids:
        return {}
    rows = db.scalars(select(Assessment).where(Assessment.opportunity_id.in_(ids)).order_by(Assessment.created_at.desc())).all()
    latest = {}
    for row in rows:
        latest.setdefault(row.opportunity_id, row)
    return latest


def _partner_names(db: Session, ids) -> dict:
    if not ids:
        return {}
    links = db.scalars(select(OpportunityPartner).where(OpportunityPartner.opportunity_id.in_(ids))).all()
    grouped = {}
    for link in links:
        grouped.setdefault(link.opportunity_id, {})[link.partner_id] = link.commitment_status
    return grouped


def _risks(db: Session, opportunity_id):
    return db.scalars(select(Risk).where(Risk.opportunity_id == opportunity_id, Risk.deleted_at.is_(None))).all()


def _commercial(db: Session, opportunity_id):
    return db.scalar(select(CommercialAssessment).where(CommercialAssessment.opportunity_id == opportunity_id))


def _opportunity_partners(db: Session, opportunity_id) -> list[dict]:
    links = db.scalars(select(OpportunityPartner).where(OpportunityPartner.opportunity_id == opportunity_id)).all()
    items = []
    for link in links:
        partner = db.get(Partner, link.partner_id)
        items.append(
            {
                "id": str(link.id),
                "partner_id": str(link.partner_id),
                "name": partner.name if partner else "",
                "role": link.role,
                "commitment_status": link.commitment_status,
                "commercial_arrangement": link.commercial_arrangement,
            }
        )
    return items


def _attachments(db: Session, entity_type: str, entity_id) -> list[dict]:
    rows = db.scalars(select(Attachment).where(Attachment.entity_type == entity_type, Attachment.entity_id == str(entity_id))).all()
    return [
        {
            "id": str(row.id),
            "file_name": row.original_file_name,
            "mime_type": row.mime_type,
            "file_size": row.file_size,
            "uploaded_at": row.uploaded_at.isoformat(),
        }
        for row in rows
    ]


def _decision(row: ManagementDecision, db: Session) -> dict:
    maker = db.get(User, row.decision_maker_id)
    return {
        "id": str(row.id),
        "assessment_id": str(row.assessment_id),
        "calculated_recommendation": row.calculated_recommendation,
        "calculated_score": _money(display_score(row.calculated_score)) if row.calculated_score is not None else None,
        "final_decision": row.final_decision,
        "override_recommendation": row.override_recommendation,
        "override_reason": row.override_reason,
        "is_override": row.is_override,
        "exception_justification": row.exception_justification,
        "decision_maker": maker.full_name if maker else "",
        "decision_date": row.decision_date.isoformat(),
    }


def _approval(row: ApprovalRecord, db: Session) -> dict:
    approver = db.get(User, row.approver_id)
    return {
        "id": str(row.id),
        "stage": row.stage,
        "decision": row.decision,
        "comments": row.comments,
        "approver": approver.full_name if approver else "",
        "previous_status": row.previous_status,
        "new_status": row.new_status,
        "decided_at": row.decided_at.isoformat(),
    }


def _money(value):
    if value is None:
        return None
    return float(to_decimal(value).quantize(Decimal("0.01")))


def _date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)
