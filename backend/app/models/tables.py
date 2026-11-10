import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def json_type():
    return JSON().with_variant(JSONB(), "postgresql")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", back_populates="users")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    users: Mapped[list[User]] = relationship(secondary="user_roles", back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(secondary="role_permissions", back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    roles: Mapped[list[Role]] = relationship(secondary="role_permissions", back_populates="permissions")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("roles.id"), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("permissions.id"), primary_key=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Sector(Base):
    __tablename__ = "sectors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class BusinessUnit(Base):
    __tablename__ = "business_units"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ServiceLine(Base):
    __tablename__ = "service_lines"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))


class Opportunity(Base, TimestampMixin):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(240))
    client_name: Mapped[str] = mapped_column(String(240))
    country_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("countries.id"))
    sector_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("sectors.id"))
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("business_units.id"))
    description: Mapped[str] = mapped_column(Text)
    opportunity_source: Mapped[str] = mapped_column(String(80))
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"))
    expected_award_date: Mapped[datetime | None] = mapped_column(Date)
    expected_start_date: Mapped[datetime | None] = mapped_column(Date)
    expected_duration: Mapped[int | None] = mapped_column(Integer)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(48), default="identified", index=True)
    strategic_importance: Mapped[str | None] = mapped_column(String(32))
    partner_required: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    country: Mapped[Country] = relationship()
    sector: Mapped[Sector] = relationship()
    business_unit: Mapped[BusinessUnit | None] = relationship()
    owner: Mapped[User] = relationship()
    service_lines: Mapped[list[ServiceLine]] = relationship(secondary="opportunity_service_lines")


class OpportunityServiceLine(Base):
    __tablename__ = "opportunity_service_lines"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("opportunities.id"), primary_key=True)
    service_line_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("service_lines.id"), primary_key=True)


class AssessmentTemplate(Base, TimestampMixin):
    __tablename__ = "assessment_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    template_type: Mapped[str] = mapped_column(String(80), default="opportunity")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))


class AssessmentTemplateVersion(Base):
    __tablename__ = "assessment_template_versions"
    __table_args__ = (UniqueConstraint("template_id", "version_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessment_templates.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    effective_from: Mapped[datetime | None] = mapped_column(Date)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gap_normalized_threshold: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0.6000"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    template: Mapped[AssessmentTemplate] = relationship()
    criteria: Mapped[list["EvaluationCriterion"]] = relationship(back_populates="version", cascade="all, delete-orphan")
    scale: Mapped["ScoringScale | None"] = relationship(back_populates="version", cascade="all, delete-orphan", uselist=False)
    rules: Mapped[list["RecommendationRule"]] = relationship(back_populates="version", cascade="all, delete-orphan")
    questions: Mapped[list["AssessmentQuestion"]] = relationship(back_populates="version", cascade="all, delete-orphan")


class ScoringScale(Base):
    __tablename__ = "scoring_scales"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assessment_template_versions.id"), unique=True
    )
    name: Mapped[str] = mapped_column(String(120), default="Default scale")
    minimum_value: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("1"))
    maximum_value: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("5"))
    version: Mapped[AssessmentTemplateVersion] = relationship(back_populates="scale")
    values: Mapped[list["ScoringScaleValue"]] = relationship(back_populates="scale", cascade="all, delete-orphan")


class ScoringScaleValue(Base):
    __tablename__ = "scoring_scale_values"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scoring_scale_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("scoring_scales.id"))
    numeric_value: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    label: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_selectable: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_justification: Mapped[bool] = mapped_column(Boolean, default=False)
    is_weak: Mapped[bool] = mapped_column(Boolean, default=False)
    scale: Mapped[ScoringScale] = relationship(back_populates="values")


class EvaluationCriterion(Base):
    __tablename__ = "evaluation_criteria"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assessment_template_versions.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    weight: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_evidence: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[AssessmentTemplateVersion] = relationship(back_populates="criteria")
    subcriteria: Mapped[list["EvaluationSubcriterion"]] = relationship(back_populates="criterion", cascade="all, delete-orphan")


class EvaluationSubcriterion(Base):
    __tablename__ = "evaluation_subcriteria"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    criterion_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("evaluation_criteria.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    weight: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scoring_guidance: Mapped[str] = mapped_column(Text, default="")
    criterion: Mapped[EvaluationCriterion] = relationship(back_populates="subcriteria")


class RecommendationRule(Base):
    __tablename__ = "recommendation_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assessment_template_versions.id"), index=True
    )
    recommendation_name: Mapped[str] = mapped_column(String(200))
    minimum_score: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    maximum_score: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    description: Mapped[str] = mapped_column(Text, default="")
    management_action: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(20), default="#1B4F8A")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[AssessmentTemplateVersion] = relationship(back_populates="rules")


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assessment_template_versions.id"), index=True
    )
    criterion_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    subcriterion_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    prompt: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String(40))
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    options: Mapped[list | None] = mapped_column(json_type())
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[AssessmentTemplateVersion] = relationship(back_populates="questions")


class RedFlagRule(Base):
    __tablename__ = "red_flag_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    parameters: Mapped[dict | None] = mapped_column(json_type())
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("opportunities.id"), index=True)
    template_version_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessment_template_versions.id"))
    assessment_number: Mapped[str] = mapped_column(String(32), unique=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    completion_percentage: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"))
    calculated_score: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    scores_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    recommendation_name: Mapped[str | None] = mapped_column(String(200))
    recommendation_final: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_red_flags: Mapped[list | None] = mapped_column(json_type())
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    parent_assessment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessments.id"))

    opportunity: Mapped[Opportunity] = relationship()
    template_version: Mapped[AssessmentTemplateVersion] = relationship()


class AssessmentAssignment(Base):
    __tablename__ = "assessment_assignments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessments.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    criterion_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))


class CriterionScore(Base):
    __tablename__ = "criterion_scores"
    __table_args__ = (UniqueConstraint("assessment_id", "criterion_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessments.id"), index=True)
    criterion_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("evaluation_criteria.id"))
    selected_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    normalized_score: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    weighted_score: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    comments: Mapped[str] = mapped_column(Text, default="")
    gaps: Mapped[str] = mapped_column(Text, default="")
    evaluator_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SubcriterionScore(Base):
    __tablename__ = "subcriterion_scores"
    __table_args__ = (UniqueConstraint("assessment_id", "subcriterion_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessments.id"), index=True)
    subcriterion_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("evaluation_subcriteria.id"))
    selected_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    normalized_score: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    comments: Mapped[str] = mapped_column(Text, default="")
    evaluator_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuestionResponse(Base):
    __tablename__ = "question_responses"
    __table_args__ = (UniqueConstraint("assessment_id", "question_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessments.id"), index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessment_questions.id"))
    response_text: Mapped[str] = mapped_column(Text, default="")
    response_json: Mapped[dict | list | None] = mapped_column(json_type())


class AssessmentEvidence(Base):
    __tablename__ = "assessment_evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessments.id"), index=True)
    criterion_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    file_name: Mapped[str] = mapped_column(String(260))
    storage_key: Mapped[str] = mapped_column(String(400))
    mime_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Risk(Base, TimestampMixin):
    __tablename__ = "risks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("opportunities.id"), index=True)
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessments.id"))
    criterion_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    reference_number: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(40))
    probability: Mapped[int] = mapped_column(Integer)
    impact: Mapped[int] = mapped_column(Integer)
    inherent_score: Mapped[int] = mapped_column(Integer)
    mitigation_plan: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    target_date: Mapped[datetime | None] = mapped_column(Date)
    residual_probability: Mapped[int | None] = mapped_column(Integer)
    residual_impact: Mapped[int | None] = mapped_column(Integer)
    residual_score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="open")
    is_regulatory_blocker: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CommercialAssessment(Base, TimestampMixin):
    __tablename__ = "commercial_assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("opportunities.id"), index=True)
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessments.id"))
    contract_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"))
    internal_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    partner_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    travel_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    third_party_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    licensing_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    other_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    bid_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    contingency: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    probability_of_winning: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"))
    assumptions: Mapped[str] = mapped_column(Text, default="")
    figures_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    gross_profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    gross_margin: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    expected_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    expected_contribution: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    partner_cost_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))


class Partner(Base, TimestampMixin):
    __tablename__ = "partners"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(240))
    country_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("countries.id"))
    description: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str] = mapped_column(String(300), default="")
    contact_name: Mapped[str] = mapped_column(String(160), default="")
    contact_email: Mapped[str] = mapped_column(String(320), default="")
    contact_phone: Mapped[str] = mapped_column(String(60), default="")
    industry: Mapped[str] = mapped_column(String(120), default="")
    healthcare_capabilities: Mapped[str] = mapped_column(Text, default="")
    technology_capabilities: Mapped[str] = mapped_column(Text, default="")
    certifications: Mapped[str] = mapped_column(Text, default="")
    project_references: Mapped[str] = mapped_column(Text, default="")
    relevant_experience: Mapped[str] = mapped_column(Text, default="")
    available_consultants: Mapped[str] = mapped_column(Text, default="")
    partnership_status: Mapped[str] = mapped_column(String(40), default="prospect")
    nda_status: Mapped[str] = mapped_column(String(40), default="not_started")
    agreement_status: Mapped[str] = mapped_column(String(40), default="none")
    commercial_arrangements: Mapped[str] = mapped_column(Text, default="")
    relationship_owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    performance_history: Mapped[str] = mapped_column(Text, default="")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    country: Mapped[Country | None] = relationship()


class PartnerCapability(Base):
    __tablename__ = "partner_capabilities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PartnerCapabilityMapping(Base):
    __tablename__ = "partner_capability_mapping"

    partner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("partners.id"), primary_key=True)
    capability_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("partner_capabilities.id"), primary_key=True)
    proficiency_level: Mapped[str] = mapped_column(String(40), default="demonstrated")
    evidence_reference: Mapped[str] = mapped_column(Text, default="")


class OpportunityPartner(Base):
    __tablename__ = "opportunity_partners"
    __table_args__ = (UniqueConstraint("opportunity_id", "partner_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("opportunities.id"), index=True)
    partner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("partners.id"))
    role: Mapped[str] = mapped_column(String(120), default="Delivery partner")
    commitment_status: Mapped[str] = mapped_column(String(40), default="proposed")
    commercial_arrangement: Mapped[str] = mapped_column(Text, default="")


class ResourceRequirement(Base, TimestampMixin):
    __tablename__ = "resource_requirements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("opportunities.id"), index=True)
    role: Mapped[str] = mapped_column(String(160))
    required_skills: Mapped[str] = mapped_column(Text, default="")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    allocation_percentage: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("100"))
    duration_months: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    resource_type: Mapped[str] = mapped_column(String(20), default="internal")
    availability_status: Mapped[str] = mapped_column(String(32), default="unconfirmed")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    identified_gap: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")


class ActionItem(Base, TimestampMixin):
    __tablename__ = "action_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_number: Mapped[str] = mapped_column(String(32), unique=True)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("opportunities.id"), index=True)
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessments.id"))
    criterion_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    title: Mapped[str] = mapped_column(String(240))
    identified_gap: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    due_date: Mapped[datetime | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), default="not_started")
    completion_notes: Mapped[str] = mapped_column(Text, default="")
    is_mandatory_for_commitment: Mapped[bool] = mapped_column(Boolean, default=False)


class ApprovalRecord(Base):
    __tablename__ = "approval_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("opportunities.id"), index=True)
    assessment_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessments.id"), index=True)
    stage: Mapped[str] = mapped_column(String(40))
    approver_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(40))
    comments: Mapped[str] = mapped_column(Text, default="")
    previous_status: Mapped[str] = mapped_column(String(48), default="")
    new_status: Mapped[str] = mapped_column(String(48), default="")
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ManagementDecision(Base):
    __tablename__ = "management_decisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("opportunities.id"), index=True)
    assessment_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assessments.id"))
    calculated_recommendation: Mapped[str] = mapped_column(String(200), default="")
    calculated_score: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    final_decision: Mapped[str] = mapped_column(String(48))
    override_recommendation: Mapped[str | None] = mapped_column(String(200))
    override_reason: Mapped[str] = mapped_column(Text, default="")
    is_override: Mapped[bool] = mapped_column(Boolean, default=False)
    exception_justification: Mapped[str] = mapped_column(Text, default="")
    decision_maker_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    decision_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(80))
    old_values: Mapped[dict | None] = mapped_column(json_type())
    new_values: Mapped[dict | None] = mapped_column(json_type())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    original_file_name: Mapped[str] = mapped_column(String(260))
    storage_key: Mapped[str] = mapped_column(String(400))
    mime_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    notification_type: Mapped[str] = mapped_column(String(40), default="info")
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
