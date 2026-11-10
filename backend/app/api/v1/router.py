import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db, minutes_from_settings
from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, hash_token, verify_password
from app.models.tables import (
    ActionItem,
    Assessment,
    AssessmentEvidence,
    AssessmentTemplate,
    Attachment,
    AuditLog,
    BusinessUnit,
    Country,
    Currency,
    Notification,
    Opportunity,
    OpportunityPartner,
    Partner,
    PartnerCapability,
    PartnerCapabilityMapping,
    Permission,
    RedFlagRule,
    RefreshToken,
    ResourceRequirement,
    Risk,
    Role,
    Sector,
    ServiceLine,
    User,
    utcnow,
)
from app.schemas import (
    ActionIn,
    AssessmentCreate,
    AssessmentUpdate,
    CommercialIn,
    DecisionIn,
    LoginIn,
    LookupIn,
    OpportunityCreate,
    OpportunityUpdate,
    PartnerIn,
    PartnerLinkIn,
    PasswordChangeIn,
    RedFlagUpdate,
    RefreshIn,
    ResourceIn,
    ReviewIn,
    RiskIn,
    SettingIn,
    TemplateCreate,
    TemplateUpdate,
    TransitionIn,
    UserCreate,
    UserUpdate,
)
from app.services.access import effective_permissions, fail, get_setting, has_permission, load_user, require_permission, set_setting
from app.services.assessments import (
    can_edit_opportunity,
    can_score,
    can_view_opportunity,
    create_assessment,
    get_assessment,
    present_assessment,
    recalculate,
    submit_assessment,
    update_assessment,
)
from app.services.portfolio import (
    activity,
    archive_opportunity,
    create_opportunity,
    link_partner,
    list_opportunities,
    present_action,
    present_commercial,
    present_opportunity,
    present_partner,
    present_resource,
    present_risk,
    resource_summary,
    save_action,
    save_commercial,
    save_resource,
    save_risk,
    transition_opportunity,
    update_opportunity,
    visible_opportunities,
)
from app.services.records import audit
from app.services.reports import assessment_report, compare_assessments, dashboard, portfolio_report, render_pdf
from app.services.templates import create_template, list_templates, present_template, publish, start_new_version, update_draft
from app.services.workflow import pending_items, record_decision, record_review

router = APIRouter()
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".txt", ".csv"}


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


@router.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.strip().lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        fail(401, "Invalid email or password")
    refresh, expires = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh), expires_at=expires))
    return {
        "access_token": create_access_token(user.id, minutes_from_settings(db)),
        "refresh_token": refresh,
        "token_type": "bearer",
    }


@router.post("/auth/refresh")
def refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    try:
        decoded = decode_token(payload.refresh_token)
    except Exception:
        fail(401, "Invalid or expired session")
    if decoded.get("type") != "refresh":
        fail(401, "Invalid token type")
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token)))
    if row is None or row.revoked or _aware(row.expires_at) < datetime.now(timezone.utc):
        fail(401, "Invalid or expired session")
    user = load_user(db, uuid.UUID(decoded["sub"]))
    if user is None or not user.is_active:
        fail(401, "User is inactive or was not found")
    row.revoked = True
    refresh_token, expires = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh_token), expires_at=expires))
    return {"access_token": create_access_token(user.id, minutes_from_settings(db)), "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/auth/logout")
def logout(payload: RefreshIn, db: Session = Depends(get_db)):
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token)))
    if row:
        row.revoked = True
    return {"status": "ok"}


@router.get("/auth/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _user_payload(user, db, include_email=True)


@router.post("/auth/change-password")
def change_password(payload: PasswordChangeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, user.password_hash):
        fail(400, "Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    for token in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False))).all():
        token.revoked = True
    return {"status": "ok"}


@router.get("/users")
def list_users(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).options(selectinload(User.roles)).order_by(User.full_name)).all()
    manage = has_permission(user, "users.manage", db)
    return [_user_payload(row, db, include_email=manage or row.id == user.id) for row in rows]


@router.post("/users")
def create_user(payload: UserCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "users.manage")
    email = payload.email.strip().lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        fail(409, "A user with this email already exists")
    roles = _roles(db, payload.role_ids)
    created = User(full_name=payload.full_name.strip(), email=email, password_hash=hash_password(payload.password), is_active=True, roles=roles)
    db.add(created)
    db.flush()
    audit(db, user_id=user.id, entity_type="user", entity_id=created.id, action="user.changed", new={"email": email, "active": True})
    return _user_payload(load_user(db, created.id), db, include_email=True)


@router.put("/users/{user_id}")
def update_user(user_id: uuid.UUID, payload: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "users.manage")
    target = load_user(db, user_id)
    if target is None:
        fail(404, "User was not found")
    if payload.full_name is not None:
        target.full_name = payload.full_name.strip()
    if payload.password:
        target.password_hash = hash_password(payload.password)
    if payload.role_ids is not None:
        target.roles = _roles(db, payload.role_ids)
    if payload.is_active is not None:
        target.is_active = payload.is_active
    _guard_last_admin(db, target)
    audit(db, user_id=user.id, entity_type="user", entity_id=target.id, action="user.changed", new={"active": target.is_active})
    return _user_payload(target, db, include_email=True)


@router.get("/roles")
def list_roles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "users.manage")
    roles = db.scalars(select(Role).options(selectinload(Role.permissions)).order_by(Role.name)).all()
    return [
        {"id": str(role.id), "name": role.name, "description": role.description, "permissions": [item.code for item in role.permissions]}
        for role in roles
    ]


@router.get("/lookups")
def lookups(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.constants import (
        ACTION_PRIORITIES,
        ACTION_STATUSES,
        AGREEMENT_STATUSES,
        AVAILABILITY_STATUSES,
        COMMITMENT_STATUSES,
        NDA_STATUSES,
        OPPORTUNITY_SOURCES,
        OPPORTUNITY_STATUSES,
        PARTNER_STATUSES,
        RESOURCE_TYPES,
        RISK_CATEGORIES,
        RISK_STATUSES,
        STRATEGIC_IMPORTANCE,
    )

    return {
        "countries": _named(db, Country),
        "sectors": _named(db, Sector),
        "business_units": _named(db, BusinessUnit),
        "service_lines": _named(db, ServiceLine),
        "currencies": [{"code": row.code, "name": row.name} for row in db.scalars(select(Currency).order_by(Currency.code)).all()],
        "capabilities": _named(db, PartnerCapability),
        "sources": OPPORTUNITY_SOURCES,
        "statuses": OPPORTUNITY_STATUSES,
        "strategic_importance": STRATEGIC_IMPORTANCE,
        "risk_categories": RISK_CATEGORIES,
        "risk_statuses": RISK_STATUSES,
        "action_statuses": ACTION_STATUSES,
        "action_priorities": ACTION_PRIORITIES,
        "partner_statuses": PARTNER_STATUSES,
        "nda_statuses": NDA_STATUSES,
        "agreement_statuses": AGREEMENT_STATUSES,
        "commitment_statuses": COMMITMENT_STATUSES,
        "resource_types": RESOURCE_TYPES,
        "availability_statuses": AVAILABILITY_STATUSES,
        "users": [{"id": str(row.id), "full_name": row.full_name} for row in db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.full_name)).all()],
    }


@router.post("/admin/lookups/{kind}")
def add_lookup(kind: str, payload: LookupIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "config.manage")
    model = {"countries": Country, "sectors": Sector, "business-units": BusinessUnit, "service-lines": ServiceLine, "capabilities": PartnerCapability}.get(kind)
    if model is None:
        fail(404, "Unknown lookup")
    if db.scalar(select(model).where(func.lower(model.name) == payload.name.strip().lower())):
        fail(409, "That value already exists")
    row = model(name=payload.name.strip())
    db.add(row)
    db.flush()
    return {"id": str(row.id), "name": row.name}


@router.get("/admin/settings")
def get_settings_route(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "config.manage")
    return {"admin_can_approve": get_setting(db, "admin_can_approve", "true"), "session_minutes": get_setting(db, "session_minutes", "60")}


@router.put("/admin/settings/{key}")
def update_setting(key: str, payload: SettingIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "config.manage")
    if key not in {"admin_can_approve", "session_minutes"}:
        fail(404, "Unknown setting")
    set_setting(db, key, payload.value.strip())
    audit(db, user_id=user.id, entity_type="setting", entity_id=key, action="settings.changed", new={"value": payload.value.strip()})
    return {"key": key, "value": payload.value.strip()}


@router.get("/admin/red-flags")
def list_flags(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "config.manage")
    rows = db.scalars(select(RedFlagRule).order_by(RedFlagRule.display_order)).all()
    return [
        {"id": str(row.id), "code": row.code, "name": row.name, "description": row.description, "is_active": row.is_active, "parameters": row.parameters}
        for row in rows
    ]


@router.put("/admin/red-flags/{flag_id}")
def update_flag(flag_id: uuid.UUID, payload: RedFlagUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "config.manage")
    row = db.get(RedFlagRule, flag_id)
    if row is None:
        fail(404, "Red flag rule was not found")
    if payload.name is not None:
        row.name = payload.name.strip()
    if payload.description is not None:
        row.description = payload.description.strip()
    if payload.is_active is not None:
        row.is_active = payload.is_active
    if payload.parameters is not None:
        row.parameters = payload.parameters
    return {"id": str(row.id), "is_active": row.is_active, "parameters": row.parameters}


@router.get("/opportunities")
def opportunities(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    search: str | None = None,
    status: str | None = None,
    country_id: uuid.UUID | None = None,
    business_unit_id: uuid.UUID | None = None,
    service_line_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    partner_id: uuid.UUID | None = None,
    recommendation: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
):
    return list_opportunities(
        db,
        user,
        search=search,
        status=status,
        country_id=country_id,
        business_unit_id=business_unit_id,
        service_line_id=service_line_id,
        owner_id=owner_id,
        partner_id=partner_id,
        recommendation=recommendation,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.post("/opportunities")
def post_opportunity(payload: OpportunityCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opportunity = create_opportunity(db, user, payload)
    db.flush()
    return _detail(db, user, opportunity.id)


@router.get("/opportunities/{opportunity_id}")
def get_opportunity(opportunity_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _detail(db, user, opportunity_id)


@router.put("/opportunities/{opportunity_id}")
def put_opportunity(opportunity_id: uuid.UUID, payload: OpportunityUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opportunity = _opportunity(db, user, opportunity_id)
    update_opportunity(db, user, opportunity, payload)
    return _detail(db, user, opportunity_id)


@router.delete("/opportunities/{opportunity_id}")
def delete_opportunity(opportunity_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opportunity = _opportunity(db, user, opportunity_id)
    archive_opportunity(db, user, opportunity)
    return {"status": "archived"}


@router.post("/opportunities/{opportunity_id}/transition")
def post_transition(opportunity_id: uuid.UUID, payload: TransitionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opportunity = _opportunity(db, user, opportunity_id)
    transition_opportunity(db, user, opportunity, payload.status)
    return _detail(db, user, opportunity_id)


@router.get("/opportunities/{opportunity_id}/history")
def history(opportunity_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _opportunity(db, user, opportunity_id)
    return activity(db, opportunity_id)


@router.get("/assessment-templates")
def templates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list_templates(db)
    return [
        {"id": str(row.id), "name": row.name, "description": row.description, "template_type": row.template_type, "status": row.status}
        for row in rows
    ]


@router.post("/assessment-templates")
def post_template(payload: TemplateCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "config.manage")
    template = create_template(db, user, payload.name, payload.description, payload.template_type)
    return present_template(db, template)


@router.get("/assessment-templates/{template_id}")
def get_template_route(template_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        fail(404, "Assessment template was not found")
    return present_template(db, template)


@router.put("/assessment-templates/{template_id}")
def put_template(template_id: uuid.UUID, payload: TemplateUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "config.manage")
    update_draft(db, user, template_id, payload)
    return present_template(db, db.get(AssessmentTemplate, template_id))


@router.post("/assessment-templates/{template_id}/publish")
def publish_template(template_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "config.manage")
    publish(db, user, template_id)
    return present_template(db, db.get(AssessmentTemplate, template_id))


@router.post("/assessment-templates/{template_id}/versions")
def new_version(template_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "config.manage")
    start_new_version(db, user, template_id)
    return present_template(db, db.get(AssessmentTemplate, template_id))


@router.get("/assessment-templates/{template_id}/versions")
def template_versions(template_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        fail(404, "Assessment template was not found")
    presented = present_template(db, template)
    return presented["versions"]


@router.get("/assessments")
def assessments(user: User = Depends(get_current_user), db: Session = Depends(get_db), opportunity_id: uuid.UUID | None = None):
    rows = db.scalars(select(Assessment).order_by(Assessment.created_at.desc())).all()
    items = []
    for row in rows:
        opportunity = db.get(Opportunity, row.opportunity_id)
        if opportunity.deleted_at is not None or not can_view_opportunity(db, user, opportunity):
            continue
        if opportunity_id and row.opportunity_id != opportunity_id:
            continue
        items.append(
            {
                "id": str(row.id),
                "assessment_number": row.assessment_number,
                "opportunity_id": str(row.opportunity_id),
                "opportunity_name": opportunity.name,
                "status": row.status,
                "calculated_score": float(row.calculated_score) if row.calculated_score is not None else None,
                "recommendation_name": row.recommendation_name,
                "completion_percentage": float(row.completion_percentage or 0),
                "template_version_id": str(row.template_version_id),
            }
        )
    return items


@router.post("/assessments")
def post_assessment(payload: AssessmentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opportunity = _opportunity(db, user, payload.opportunity_id)
    assessment = create_assessment(db, user, opportunity, payload.template_id, payload.parent_assessment_id)
    return present_assessment(db, user, assessment)


@router.get("/assessments/{assessment_id}")
def get_assessment_route(assessment_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return present_assessment(db, user, get_assessment(db, assessment_id))


@router.put("/assessments/{assessment_id}")
def put_assessment(assessment_id: uuid.UUID, payload: AssessmentUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    assessment = get_assessment(db, assessment_id)
    update_assessment(db, user, assessment, payload)
    return present_assessment(db, user, assessment)


@router.post("/assessments/{assessment_id}/submit")
def post_submit(assessment_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    assessment = get_assessment(db, assessment_id)
    submit_assessment(db, user, assessment)
    return present_assessment(db, user, assessment)


@router.post("/assessments/{assessment_id}/recalculate")
def post_recalculate(assessment_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    assessment = get_assessment(db, assessment_id)
    present_assessment(db, user, assessment)
    recalculate(db, assessment)
    return present_assessment(db, user, assessment)


@router.get("/assessments/{assessment_id}/result")
def assessment_result(assessment_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return present_assessment(db, user, get_assessment(db, assessment_id))


@router.post("/assessments/{assessment_id}/evidence")
def upload_evidence(
    assessment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    criterion_id: uuid.UUID | None = Form(default=None),
):
    assessment = get_assessment(db, assessment_id)
    if not can_score(db, user, assessment, criterion_id):
        fail(403, "You do not have permission to add evidence")
    stored = _store_file(file)
    evidence = AssessmentEvidence(
        assessment_id=assessment.id,
        criterion_id=criterion_id,
        file_name=stored[0],
        storage_key=stored[1],
        mime_type=file.content_type or "application/octet-stream",
        file_size=stored[2],
        uploaded_by=user.id,
    )
    db.add(evidence)
    db.flush()
    return {"id": str(evidence.id), "file_name": evidence.file_name}


@router.post("/assessments/{assessment_id}/reviews")
def post_review(assessment_id: uuid.UUID, payload: ReviewIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record_review(db, user, assessment_id, payload.stage, payload.decision, payload.comments)
    return present_assessment(db, user, get_assessment(db, assessment_id))


@router.post("/assessments/{assessment_id}/approve")
@router.post("/assessments/{assessment_id}/reject")
@router.post("/assessments/{assessment_id}/return")
def post_decision_alias(assessment_id: uuid.UUID, payload: DecisionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record_decision(db, user, assessment_id, payload)
    return present_assessment(db, user, get_assessment(db, assessment_id))


@router.get("/approvals/pending")
def approvals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return pending_items(db, user)


@router.get("/opportunities/{opportunity_id}/risks")
def list_risks(opportunity_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _opportunity(db, user, opportunity_id)
    rows = db.scalars(select(Risk).where(Risk.opportunity_id == opportunity_id, Risk.deleted_at.is_(None))).all()
    return [present_risk(row) for row in rows]


@router.post("/opportunities/{opportunity_id}/risks")
def post_risk(opportunity_id: uuid.UUID, payload: RiskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opportunity = _opportunity(db, user, opportunity_id)
    risk = save_risk(db, user, opportunity, payload)
    db.flush()
    return present_risk(risk)


@router.put("/risks/{risk_id}")
def put_risk(risk_id: uuid.UUID, payload: RiskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    risk = db.get(Risk, risk_id)
    if risk is None or risk.deleted_at is not None:
        fail(404, "Risk was not found")
    opportunity = _opportunity(db, user, risk.opportunity_id)
    save_risk(db, user, opportunity, payload, risk)
    return present_risk(risk)


@router.delete("/risks/{risk_id}")
def delete_risk(risk_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    risk = db.get(Risk, risk_id)
    if risk is None:
        fail(404, "Risk was not found")
    _opportunity(db, user, risk.opportunity_id)
    if not can_edit_opportunity(db, user, db.get(Opportunity, risk.opportunity_id)):
        fail(403, "You do not have permission to archive this risk")
    risk.deleted_at = utcnow()
    return {"status": "archived"}


@router.get("/risks")
def all_risks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = [row.id for row in db.scalars(visible_opportunities(db, user)).all()]
    rows = db.scalars(select(Risk).where(Risk.deleted_at.is_(None), Risk.opportunity_id.in_(ids or [uuid.uuid4()]))).all()
    return [present_risk(row) for row in rows]


@router.get("/opportunities/{opportunity_id}/commercial")
def get_commercial(opportunity_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    detail = _detail(db, user, opportunity_id)
    return detail["commercial"]


@router.post("/opportunities/{opportunity_id}/commercial")
@router.put("/opportunities/{opportunity_id}/commercial")
def put_commercial(opportunity_id: uuid.UUID, payload: CommercialIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opportunity = _opportunity(db, user, opportunity_id)
    row = save_commercial(db, user, opportunity, payload)
    return present_commercial(row)


@router.put("/commercial/{commercial_id}")
def put_commercial_by_id(commercial_id: uuid.UUID, payload: CommercialIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.tables import CommercialAssessment

    row = db.get(CommercialAssessment, commercial_id)
    if row is None:
        fail(404, "Commercial assessment was not found")
    opportunity = _opportunity(db, user, row.opportunity_id)
    saved = save_commercial(db, user, opportunity, payload)
    return present_commercial(saved)


@router.get("/commercial")
def all_commercial(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.tables import CommercialAssessment

    ids = [row.id for row in db.scalars(visible_opportunities(db, user)).all()]
    rows = db.scalars(select(CommercialAssessment).where(CommercialAssessment.opportunity_id.in_(ids or [uuid.uuid4()]))).all()
    return [present_commercial(row) for row in rows]


@router.get("/partners")
def partners(user: User = Depends(get_current_user), db: Session = Depends(get_db), search: str | None = None):
    statement = select(Partner).where(Partner.deleted_at.is_(None)).options(selectinload(Partner.country)).order_by(Partner.name)
    if search:
        statement = statement.where(Partner.name.ilike(f"%{search.strip()}%"))
    return [present_partner(db, row) for row in db.scalars(statement).all()]


@router.post("/partners")
def post_partner(payload: PartnerIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "partners.manage")
    partner = _apply_partner(db, Partner(name=payload.name.strip()), payload)
    db.add(partner)
    db.flush()
    return present_partner(db, partner)


@router.get("/partners/{partner_id}")
def get_partner(partner_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    partner = db.scalar(select(Partner).where(Partner.id == partner_id).options(selectinload(Partner.country)))
    if partner is None or partner.deleted_at is not None:
        fail(404, "Partner was not found")
    return present_partner(db, partner)


@router.put("/partners/{partner_id}")
def put_partner(partner_id: uuid.UUID, payload: PartnerIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(user, db, "partners.manage")
    partner = db.get(Partner, partner_id)
    if partner is None or partner.deleted_at is not None:
        fail(404, "Partner was not found")
    _apply_partner(db, partner, payload)
    return present_partner(db, partner)


@router.post("/opportunities/{opportunity_id}/partners")
def post_link(opportunity_id: uuid.UUID, payload: PartnerLinkIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opportunity = _opportunity(db, user, opportunity_id)
    link_partner(db, user, opportunity, payload)
    return _detail(db, user, opportunity_id)["partners"]


@router.delete("/opportunities/{opportunity_id}/partners/{partner_id}")
def delete_link(opportunity_id: uuid.UUID, partner_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opportunity = _opportunity(db, user, opportunity_id)
    if not can_edit_opportunity(db, user, opportunity):
        fail(403, "You do not have permission to unlink partners")
    row = db.scalar(select(OpportunityPartner).where(OpportunityPartner.opportunity_id == opportunity_id, OpportunityPartner.partner_id == partner_id))
    if row:
        db.delete(row)
    return {"status": "removed"}


@router.get("/resources")
def resources(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = [row.id for row in db.scalars(visible_opportunities(db, user)).all()]
    rows = db.scalars(select(ResourceRequirement).where(ResourceRequirement.opportunity_id.in_(ids or [uuid.uuid4()]))).all()
    return {"items": [present_resource(row) for row in rows], "summary": resource_summary(rows)}


@router.post("/opportunities/{opportunity_id}/resources")
def post_resource(opportunity_id: uuid.UUID, payload: ResourceIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opportunity = _opportunity(db, user, opportunity_id)
    row = save_resource(db, user, opportunity, payload)
    db.flush()
    return present_resource(row)


@router.put("/resources/{resource_id}")
def put_resource(resource_id: uuid.UUID, payload: ResourceIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(ResourceRequirement, resource_id)
    if row is None:
        fail(404, "Resource requirement was not found")
    opportunity = _opportunity(db, user, row.opportunity_id)
    save_resource(db, user, opportunity, payload, row)
    return present_resource(row)


@router.get("/actions")
def actions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = [row.id for row in db.scalars(visible_opportunities(db, user)).all()]
    rows = db.scalars(select(ActionItem).where(ActionItem.opportunity_id.in_(ids or [uuid.uuid4()]))).all()
    return [present_action(row) for row in rows]


@router.post("/opportunities/{opportunity_id}/actions")
def post_action(opportunity_id: uuid.UUID, payload: ActionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opportunity = _opportunity(db, user, opportunity_id)
    row = save_action(db, user, opportunity, payload)
    db.flush()
    return present_action(row)


@router.put("/actions/{action_id}")
def put_action(action_id: uuid.UUID, payload: ActionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(ActionItem, action_id)
    if row is None:
        fail(404, "Action was not found")
    opportunity = _opportunity(db, user, row.opportunity_id)
    save_action(db, user, opportunity, payload, row)
    return present_action(row)


@router.post("/attachments")
def upload_attachment(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    entity_id: uuid.UUID = Form(...),
):
    if entity_type != "opportunity":
        fail(400, "Attachments can be added to an opportunity")
    _opportunity(db, user, entity_id)
    if not can_edit_opportunity(db, user, db.get(Opportunity, entity_id)):
        fail(403, "You do not have permission to add documents")
    stored = _store_file(file)
    row = Attachment(
        entity_type=entity_type,
        entity_id=str(entity_id),
        original_file_name=stored[0],
        storage_key=stored[1],
        mime_type=file.content_type or "application/octet-stream",
        file_size=stored[2],
        uploaded_by=user.id,
    )
    db.add(row)
    db.flush()
    return {"id": str(row.id), "file_name": row.original_file_name}


@router.get("/attachments/{attachment_id}")
def download_attachment(attachment_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Attachment, attachment_id)
    evidence = None
    if row is None:
        evidence = db.get(AssessmentEvidence, attachment_id)
        if evidence is None:
            fail(404, "File was not found")
        assessment = get_assessment(db, evidence.assessment_id)
        _opportunity(db, user, assessment.opportunity_id)
        key = evidence.storage_key
        name = evidence.file_name
    else:
        if row.entity_type == "opportunity":
            _opportunity(db, user, uuid.UUID(row.entity_id))
        key = row.storage_key
        name = row.original_file_name
    path = Path(get_settings().storage_path) / key
    if not path.exists():
        fail(404, "File was not found")
    return FileResponse(path, filename=name)


@router.get("/notifications")
def notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(30)).all()
    return [
        {
            "id": str(row.id),
            "title": row.title,
            "message": row.message,
            "notification_type": row.notification_type,
            "is_read": row.is_read,
            "created_at": row.created_at.isoformat(),
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
        }
        for row in rows
    ]


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Notification, notification_id)
    if row is None or row.user_id != user.id:
        fail(404, "Notification was not found")
    row.is_read = True
    return {"status": "ok"}


@router.get("/audit-logs")
def audit_logs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    action: str | None = None,
    entity_type: str | None = None,
    page: int = 1,
    page_size: int = 30,
):
    require_permission(user, db, "audit.view")
    statement = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        statement = statement.where(AuditLog.action == action)
    if entity_type:
        statement = statement.where(AuditLog.entity_type == entity_type)
    rows = db.scalars(statement).all()
    start = (max(page, 1) - 1) * min(page_size, 100)
    users = {item.id: item.full_name for item in db.scalars(select(User)).all()}
    page_rows = rows[start : start + min(page_size, 100)]
    return {
        "total": len(rows),
        "items": [
            {
                "id": str(row.id),
                "actor": users.get(row.user_id, "System"),
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "action": row.action,
                "old_values": row.old_values,
                "new_values": row.new_values,
                "created_at": row.created_at.isoformat(),
            }
            for row in page_rows
        ],
    }


@router.get("/reports/dashboard")
def report_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: str | None = None,
    country_id: uuid.UUID | None = None,
    business_unit_id: uuid.UUID | None = None,
    service_line_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    partner_id: uuid.UUID | None = None,
    recommendation: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    return dashboard(db, user, _filters(locals()))


@router.get("/reports/opportunities")
def report_portfolio(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: str | None = None,
    country_id: uuid.UUID | None = None,
    business_unit_id: uuid.UUID | None = None,
    service_line_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    partner_id: uuid.UUID | None = None,
    recommendation: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    return portfolio_report(db, user, _filters(locals()))


@router.get("/reports/assessment/{assessment_id}")
def report_assessment(assessment_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return assessment_report(db, user, assessment_id)


@router.get("/reports/assessment/{assessment_id}/pdf")
def report_pdf(assessment_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = assessment_report(db, user, assessment_id)
    content = render_pdf(report)
    filename = f"{report['assessment']['assessment_number']}.pdf"
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/reports/compare")
def report_compare(ids: str = Query(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    parsed = []
    for part in ids.split(","):
        if part.strip():
            parsed.append(uuid.UUID(part.strip()))
    return compare_assessments(db, user, parsed)


def _filters(values: dict) -> dict:
    keys = ["status", "country_id", "business_unit_id", "service_line_id", "owner_id", "partner_id", "recommendation", "date_from", "date_to"]
    return {key: values.get(key) for key in keys}


def _user_payload(user: User, db: Session, include_email: bool) -> dict:
    payload = {
        "id": str(user.id),
        "full_name": user.full_name,
        "roles": [role.name for role in user.roles],
        "is_active": user.is_active,
    }
    if include_email:
        payload["email"] = user.email
        payload["permissions"] = effective_permissions(user, db)
    return payload


def _roles(db: Session, role_ids: list[uuid.UUID]) -> list[Role]:
    roles = db.scalars(select(Role).where(Role.id.in_(role_ids))).all()
    if len(roles) != len(set(role_ids)):
        fail(400, "One or more roles were not found")
    return list(roles)


def _guard_last_admin(db: Session, target: User) -> None:
    admin_role = db.scalar(select(Role).where(Role.name == "System Administrator"))
    if admin_role is None:
        return
    admins = db.scalars(select(User).join(User.roles).where(Role.id == admin_role.id, User.is_active.is_(True))).all()
    still_admin = any(role.id == admin_role.id for role in target.roles) and target.is_active
    if not still_admin and all(admin.id == target.id for admin in admins):
        fail(400, "The last active system administrator cannot be removed")


def _named(db: Session, model):
    return [{"id": str(row.id), "name": row.name} for row in db.scalars(select(model).where(model.is_active.is_(True)).order_by(model.name)).all()]


def _opportunity(db: Session, user: User, opportunity_id) -> Opportunity:
    opportunity = db.scalar(
        select(Opportunity)
        .where(Opportunity.id == opportunity_id, Opportunity.deleted_at.is_(None))
        .options(
            selectinload(Opportunity.country),
            selectinload(Opportunity.sector),
            selectinload(Opportunity.business_unit),
            selectinload(Opportunity.owner),
            selectinload(Opportunity.service_lines),
        )
    )
    if opportunity is None:
        fail(404, "Opportunity was not found")
    if not can_view_opportunity(db, user, opportunity):
        fail(403, "You do not have permission to view this opportunity")
    return opportunity


def _detail(db: Session, user: User, opportunity_id):
    opportunity = _opportunity(db, user, opportunity_id)
    return present_opportunity(db, opportunity, detailed=True)


def _apply_partner(db: Session, partner: Partner, payload: PartnerIn) -> Partner:
    for field in [
        "name",
        "description",
        "website",
        "contact_name",
        "contact_email",
        "contact_phone",
        "industry",
        "healthcare_capabilities",
        "technology_capabilities",
        "certifications",
        "project_references",
        "relevant_experience",
        "available_consultants",
        "partnership_status",
        "nda_status",
        "agreement_status",
        "commercial_arrangements",
        "performance_history",
    ]:
        setattr(partner, field, getattr(payload, field) or "")
    partner.name = payload.name.strip()
    partner.country_id = payload.country_id
    partner.relationship_owner_id = payload.relationship_owner_id
    db.flush()
    db.query(PartnerCapabilityMapping).filter(PartnerCapabilityMapping.partner_id == partner.id).delete()
    for item in payload.capabilities:
        capability_id = item.get("capability_id")
        if capability_id is None or db.get(PartnerCapability, uuid.UUID(str(capability_id))) is None:
            fail(400, "A partner capability was not found")
        db.add(
            PartnerCapabilityMapping(
                partner_id=partner.id,
                capability_id=uuid.UUID(str(capability_id)),
                proficiency_level=item.get("proficiency_level") or "demonstrated",
                evidence_reference=item.get("evidence_reference") or "",
            )
        )
    return partner


def _store_file(file: UploadFile) -> tuple[str, str, int]:
    name = Path(file.filename or "upload").name
    extension = Path(name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        fail(400, "Upload a PDF, image, Word, Excel, CSV, or text file")
    content = file.file.read()
    if not content:
        fail(400, "The file is empty")
    if len(content) > 10 * 1024 * 1024:
        fail(400, "Files must be 10 MB or smaller")
    key = f"{uuid.uuid4().hex}{extension}"
    folder = Path(get_settings().storage_path)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / key).write_bytes(content)
    return name, key, len(content)
