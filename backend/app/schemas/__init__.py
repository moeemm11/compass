import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: str
    password: str = Field(min_length=8, max_length=72)
    role_ids: list[uuid.UUID] = Field(min_length=1)


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    role_ids: list[uuid.UUID] | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)


class OpportunityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=240)
    client_name: str = Field(min_length=2, max_length=240)
    country_id: uuid.UUID
    sector_id: uuid.UUID
    business_unit_id: uuid.UUID | None = None
    description: str = Field(min_length=5)
    service_line_ids: list[uuid.UUID] = Field(min_length=1)
    opportunity_source: str
    estimated_value: Decimal | None = Field(default=None, ge=0)
    currency_code: str = Field(min_length=3, max_length=3)
    expected_award_date: date | None = None
    expected_start_date: date | None = None
    expected_duration: int | None = Field(default=None, ge=0)
    owner_id: uuid.UUID
    strategic_importance: str | None = None
    partner_required: bool = False


class OpportunityUpdate(BaseModel):
    name: str | None = None
    client_name: str | None = None
    country_id: uuid.UUID | None = None
    sector_id: uuid.UUID | None = None
    business_unit_id: uuid.UUID | None = None
    description: str | None = None
    service_line_ids: list[uuid.UUID] | None = None
    opportunity_source: str | None = None
    estimated_value: Decimal | None = Field(default=None, ge=0)
    currency_code: str | None = None
    expected_award_date: date | None = None
    expected_start_date: date | None = None
    expected_duration: int | None = None
    owner_id: uuid.UUID | None = None
    strategic_importance: str | None = None
    partner_required: bool | None = None


class TransitionIn(BaseModel):
    status: str


class TemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = ""
    template_type: str = "opportunity"


class SubcriterionIn(BaseModel):
    name: str
    description: str = ""
    weight: Decimal
    is_mandatory: bool = True
    is_active: bool = True
    scoring_guidance: str = ""


class CriterionIn(BaseModel):
    name: str
    description: str = ""
    weight: Decimal
    is_mandatory: bool = True
    is_active: bool = True
    requires_evidence: bool = False
    subcriteria: list[SubcriterionIn] = []


class ScaleValueIn(BaseModel):
    numeric_value: Decimal
    label: str
    description: str = ""
    is_selectable: bool = True
    requires_justification: bool = False
    is_weak: bool = False


class ScaleIn(BaseModel):
    name: str = "Default scale"
    minimum_value: Decimal
    maximum_value: Decimal
    values: list[ScaleValueIn]


class RuleIn(BaseModel):
    recommendation_name: str
    minimum_score: Decimal
    maximum_score: Decimal
    description: str = ""
    management_action: str = ""
    color: str = "#1B4F8A"
    priority: int = 0


class QuestionIn(BaseModel):
    prompt: str
    question_type: str
    is_mandatory: bool = False
    is_active: bool = True
    options: list[str] | None = None
    criterion_index: int | None = None


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    template_type: str | None = None
    gap_normalized_threshold: Decimal | None = None
    criteria: list[CriterionIn] | None = None
    scale: ScaleIn | None = None
    recommendation_rules: list[RuleIn] | None = None
    questions: list[QuestionIn] | None = None


class AssessmentCreate(BaseModel):
    opportunity_id: uuid.UUID
    template_id: uuid.UUID
    parent_assessment_id: uuid.UUID | None = None


class AssignmentIn(BaseModel):
    user_id: uuid.UUID
    criterion_id: uuid.UUID | None = None


class CriterionScoreIn(BaseModel):
    criterion_id: uuid.UUID
    selected_score: Decimal | None = None
    comments: str | None = None
    gaps: str | None = None


class SubcriterionScoreIn(BaseModel):
    subcriterion_id: uuid.UUID
    selected_score: Decimal | None = None
    comments: str | None = None


class ResponseIn(BaseModel):
    question_id: uuid.UUID
    response_text: str | None = None
    response_json: dict | list | None = None


class AssessmentUpdate(BaseModel):
    assignments: list[AssignmentIn] | None = None
    criterion_scores: list[CriterionScoreIn] | None = None
    subcriterion_scores: list[SubcriterionScoreIn] | None = None
    responses: list[ResponseIn] | None = None


class ReviewIn(BaseModel):
    stage: str
    decision: str
    comments: str


class DecisionIn(BaseModel):
    decision: str
    comments: str
    override_recommendation: str | None = None
    override_reason: str | None = None
    exception_justification: str | None = None
    mandatory_action_ids: list[uuid.UUID] | None = None


class CommercialIn(BaseModel):
    contract_value: Decimal = Field(ge=0)
    currency_code: str
    internal_cost: Decimal = Field(default=0, ge=0)
    partner_cost: Decimal = Field(default=0, ge=0)
    travel_cost: Decimal = Field(default=0, ge=0)
    third_party_cost: Decimal = Field(default=0, ge=0)
    licensing_cost: Decimal = Field(default=0, ge=0)
    other_cost: Decimal = Field(default=0, ge=0)
    bid_cost: Decimal = Field(default=0, ge=0)
    contingency: Decimal = Field(default=0, ge=0)
    probability_of_winning: Decimal = Field(ge=0, le=100)
    assumptions: str = ""
    figures_confirmed: bool = False
    assessment_id: uuid.UUID | None = None


class RiskIn(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    description: str = ""
    category: str
    probability: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    mitigation_plan: str = ""
    owner_id: uuid.UUID | None = None
    target_date: date | None = None
    residual_probability: int | None = Field(default=None, ge=1, le=5)
    residual_impact: int | None = Field(default=None, ge=1, le=5)
    status: str = "open"
    assessment_id: uuid.UUID | None = None
    criterion_id: uuid.UUID | None = None
    is_regulatory_blocker: bool = False


class ResourceIn(BaseModel):
    role: str
    required_skills: str = ""
    quantity: int = Field(ge=1)
    allocation_percentage: Decimal = Field(default=100, ge=0, le=100)
    duration_months: Decimal | None = None
    resource_type: str = "internal"
    availability_status: str = "unconfirmed"
    owner_id: uuid.UUID | None = None
    identified_gap: bool = False
    notes: str = ""


class ActionIn(BaseModel):
    title: str
    identified_gap: str = ""
    description: str = ""
    owner_id: uuid.UUID | None = None
    priority: str = "medium"
    due_date: date | None = None
    status: str = "not_started"
    completion_notes: str = ""
    is_mandatory_for_commitment: bool = False
    assessment_id: uuid.UUID | None = None
    criterion_id: uuid.UUID | None = None


class PartnerLinkIn(BaseModel):
    partner_id: uuid.UUID
    role: str = "Delivery partner"
    commitment_status: str = "proposed"
    commercial_arrangement: str = ""


class PartnerIn(BaseModel):
    name: str = Field(min_length=2)
    country_id: uuid.UUID | None = None
    description: str = ""
    website: str = ""
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    industry: str = ""
    healthcare_capabilities: str = ""
    technology_capabilities: str = ""
    certifications: str = ""
    project_references: str = ""
    relevant_experience: str = ""
    available_consultants: str = ""
    partnership_status: str = "prospect"
    nda_status: str = "not_started"
    agreement_status: str = "none"
    commercial_arrangements: str = ""
    relationship_owner_id: uuid.UUID | None = None
    performance_history: str = ""
    capabilities: list[dict] = []


class LookupIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class RedFlagUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    parameters: dict | None = None


class SettingIn(BaseModel):
    value: str
