from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.tables import (
    AssessmentQuestion,
    BusinessUnit,
    Country,
    Currency,
    EvaluationCriterion,
    Partner,
    PartnerCapability,
    PartnerCapabilityMapping,
    Permission,
    QuestionResponse,
    RedFlagRule,
    Role,
    Sector,
    ServiceLine,
    SubcriterionScore,
    User,
)
from app.schemas import (
    CommercialIn,
    DecisionIn,
    OpportunityCreate,
    PartnerLinkIn,
    ResourceIn,
    RiskIn,
)
from app.services.access import set_setting
from app.services.assessments import create_assessment, recalculate, submit_assessment
from app.services.constants import PERMISSIONS, ROLE_DESCRIPTIONS, ROLE_PERMISSIONS
from app.services.portfolio import create_opportunity, link_partner, save_commercial, save_resource, save_risk, transition_opportunity
from app.services.templates import install_standard_template
from app.services.workflow import record_decision, record_review

DEMO_PASSWORD = "Compass123!"

USERS = [
    ("System Administrator", "admin@diyar.local", "System Administrator"),
    ("Business Development Manager", "bd@diyar.local", "Business Development Manager"),
    ("Assessment Evaluator", "evaluator@diyar.local", "Assessment Evaluator"),
    ("Functional Reviewer", "functional@diyar.local", "Functional Reviewer"),
    ("Commercial Reviewer", "commercial@diyar.local", "Commercial Reviewer"),
    ("Executive Approver", "executive@diyar.local", "Executive Approver"),
    ("Executive Viewer", "viewer@diyar.local", "Executive Viewer"),
]


def seed_database(db: Session) -> None:
    if db.scalar(select(User.id).limit(1)):
        return
    permissions = {}
    for code, description in PERMISSIONS:
        permission = Permission(code=code, description=description)
        db.add(permission)
        permissions[code] = permission
    db.flush()
    roles = {}
    for name, codes in ROLE_PERMISSIONS.items():
        role = Role(name=name, description=ROLE_DESCRIPTIONS[name], permissions=[permissions[code] for code in codes])
        db.add(role)
        roles[name] = role
    db.flush()
    password_hash = hash_password(DEMO_PASSWORD)
    users = {}
    for full_name, email, role_name in USERS:
        account = User(full_name=full_name, email=email, password_hash=password_hash, is_active=True, roles=[roles[role_name]])
        db.add(account)
        users[email] = account
    db.flush()
    countries = _add_named(db, Country, ["United Arab Emirates", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman", "Egypt", "Jordan", "United Kingdom"])
    sectors = _add_named(db, Sector, ["Public Healthcare", "Private Healthcare", "Government", "Life Sciences"])
    units = _add_named(db, BusinessUnit, ["Consulting", "Digital Delivery", "Managed Services"])
    lines = _add_named(
        db,
        ServiceLine,
        [
            "HIS / EHR Implementation",
            "Healthcare Advisory",
            "Digital Health",
            "Clinical Informatics",
            "Integration and Interoperability",
            "Cybersecurity",
            "SAP Healthcare",
            "AI and Analytics",
            "HIMSS EMRAM",
        ],
    )
    for code, name in [("AED", "UAE Dirham"), ("SAR", "Saudi Riyal"), ("QAR", "Qatari Riyal"), ("KWD", "Kuwaiti Dinar"), ("BHD", "Bahraini Dinar"), ("OMR", "Omani Rial"), ("USD", "US Dollar"), ("EUR", "Euro"), ("EGP", "Egyptian Pound"), ("GBP", "British Pound")]:
        db.add(Currency(code=code, name=name))
    capabilities = _add_named(
        db,
        PartnerCapability,
        ["SAP Healthcare", "HIS / EHR", "Digital Health", "HIMSS EMRAM", "Healthcare Advisory", "Clinical Informatics", "AI and Analytics", "Integration and Interoperability", "Cybersecurity"],
    )
    for order, (code, name, description, parameters) in enumerate(
        [
            ("negative_margin", "Negative expected gross margin", "Escalate when expected gross profit is below zero.", {}),
            ("missing_partner", "No confirmed delivery partner", "Escalate when a partner is mandatory and none is confirmed or contracted.", {"confirmed_statuses": ["confirmed", "contracted"]}),
            ("critical_resource_gap", "Critical resource gap", "Escalate when a required role is marked as a gap.", {}),
            ("critical_risk", "Critical open risk", "Escalate when an open risk's inherent score reaches the configured threshold.", {"min_inherent_score": 15}),
            ("regulatory_blocker", "Regulatory requirement not satisfied", "Escalate when a risk is marked as a regulatory blocker and remains open.", {}),
        ]
    ):
        db.add(RedFlagRule(code=code, name=name, description=description, is_active=True, parameters=parameters, display_order=order))
    set_setting(db, "admin_can_approve", "true")
    set_setting(db, "session_minutes", "60")
    db.flush()
    install_standard_template(db, users["admin@diyar.local"])
    if get_settings().seed_sample_data:
        _seed_samples(db, users, countries, sectors, units, lines, capabilities)


def _add_named(db: Session, model, names: list[str]) -> dict:
    rows = {}
    for name in names:
        row = model(name=name, is_active=True)
        db.add(row)
        rows[name] = row
    db.flush()
    return rows


def _seed_samples(db, users, countries, sectors, units, lines, capabilities) -> None:
    bd = users["bd@diyar.local"]
    partner = Partner(
        name="Sample Partner — HIS Delivery",
        country_id=countries["United Arab Emirates"].id,
        description="Demonstration partner used to show capability and commitment tracking.",
        partnership_status="active",
        nda_status="executed",
        agreement_status="executed",
        healthcare_capabilities="HIS implementation and clinical workflow design.",
        relationship_owner_id=bd.id,
    )
    db.add(partner)
    db.flush()
    db.add(PartnerCapabilityMapping(partner_id=partner.id, capability_id=capabilities["HIS / EHR"].id, proficiency_level="demonstrated", evidence_reference="Sample reference"))
    template = db.scalar(select(__import__("app.models.tables", fromlist=["AssessmentTemplate"]).AssessmentTemplate))
    common = dict(
        country_id=countries["United Arab Emirates"].id,
        sector_id=sectors["Public Healthcare"].id,
        business_unit_id=units["Digital Delivery"].id,
        service_line_ids=[lines["HIS / EHR Implementation"].id, lines["Integration and Interoperability"].id],
        opportunity_source="Government Tender",
        currency_code="AED",
        owner_id=bd.id,
        strategic_importance="high",
    )
    awaiting = create_opportunity(
        db,
        bd,
        OpportunityCreate(
            name="Sample: Regional HIS Modernisation",
            client_name="Sample Health Authority",
            description="Demonstration opportunity scored to 77 so the conditional recommendation, gaps, and executive inbox can be reviewed.",
            estimated_value=Decimal("4800000"),
            expected_duration=18,
            partner_required=True,
            **common,
        ),
    )
    save_commercial(
        db,
        bd,
        awaiting,
        CommercialIn(
            contract_value=Decimal("4800000"),
            currency_code="AED",
            internal_cost=Decimal("2200000"),
            partner_cost=Decimal("900000"),
            travel_cost=Decimal("80000"),
            third_party_cost=Decimal("60000"),
            licensing_cost=Decimal("120000"),
            other_cost=Decimal("40000"),
            contingency=Decimal("150000"),
            bid_cost=Decimal("75000"),
            probability_of_winning=Decimal("60"),
            assumptions="Sample planning assumptions. These figures are estimates.",
            figures_confirmed=False,
        ),
    )
    link_partner(db, bd, awaiting, PartnerLinkIn(partner_id=partner.id, role="HIS delivery partner", commitment_status="confirmed", commercial_arrangement="Subcontract"))
    save_resource(
        db,
        bd,
        awaiting,
        ResourceIn(role="Integration architect", required_skills="HL7 FHIR", quantity=1, allocation_percentage=Decimal("80"), duration_months=Decimal("12"), resource_type="internal", availability_status="gap", identified_gap=True),
    )
    save_risk(
        db,
        bd,
        awaiting,
        RiskIn(title="Interface timeline slips", description="Client integration environments may not be ready.", category="Technical", probability=3, impact=3, mitigation_plan="Confirm environment dates before bid submission.", status="open"),
    )
    _drive(db, users, awaiting, template.id, _pattern(5, 4, 3, 4, 4, 3, 4), "awaiting")

    create_opportunity(
        db,
        bd,
        OpportunityCreate(
            name="Sample: Private Hospital Advisory",
            client_name="Sample Private Hospital",
            description="Early-stage opportunity that has been identified and has not yet been assessed.",
            estimated_value=Decimal("900000"),
            opportunity_source="Existing Client",
            currency_code="AED",
            owner_id=bd.id,
            country_id=countries["Saudi Arabia"].id,
            sector_id=sectors["Private Healthcare"].id,
            business_unit_id=units["Consulting"].id,
            service_line_ids=[lines["Healthcare Advisory"].id],
            strategic_importance="medium",
        ),
    )
    approved = create_opportunity(
        db,
        bd,
        OpportunityCreate(
            name="Sample: Digital Health Programme",
            client_name="Sample Provider Group",
            description="Demonstration of a score at 88 and an approval that follows the system recommendation.",
            estimated_value=Decimal("2500000"),
            **common,
        ),
    )
    _drive(db, users, approved, template.id, _pattern(5, 3, 4, 5, 5, 3, 5), "approved")
    rejected = create_opportunity(
        db,
        bd,
        OpportunityCreate(
            name="Sample: Legacy Migration",
            client_name="Sample Ministry",
            description="Demonstration of a weak score and a recorded rejection.",
            estimated_value=Decimal("1500000"),
            **common,
        ),
    )
    _drive(db, users, rejected, template.id, _pattern(1, 1, 1, 1, 1, 1, 1), "rejected")
    won = create_opportunity(
        db,
        bd,
        OpportunityCreate(
            name="Sample: EMRAM Advisory",
            client_name="Sample Medical City",
            description="Demonstration of a won outcome after approval.",
            estimated_value=Decimal("1200000"),
            **common,
        ),
    )
    _drive(db, users, won, template.id, _pattern(5, 5, 5, 5, 5, 5, 5), "won")
    lost = create_opportunity(
        db,
        bd,
        OpportunityCreate(
            name="Sample: Analytics Platform",
            client_name="Sample Insurer",
            description="Demonstration of a lost outcome after the bid was submitted.",
            estimated_value=Decimal("2100000"),
            **common,
        ),
    )
    _drive(db, users, lost, template.id, _pattern(5, 4, 5, 4, 5, 4, 5), "lost")


def _pattern(*scores: int) -> dict[str, int]:
    names = [
        "Strategic Business Value",
        "Client Opportunity & Probability of Winning",
        "Technical Delivery Capability",
        "Partner Credibility & Commitment",
        "Commercial Attractiveness",
        "Resource Availability & Delivery Feasibility",
        "Risk Management",
    ]
    return dict(zip(names, scores))


def _drive(db, users, opportunity, template_id, pattern: dict[str, int], target: str) -> None:
    bd = users["bd@diyar.local"]
    assessment = create_assessment(db, bd, opportunity, template_id)
    criteria = db.scalars(
        select(EvaluationCriterion)
        .where(EvaluationCriterion.template_version_id == assessment.template_version_id)
        .options(selectinload(EvaluationCriterion.subcriteria))
    ).all()
    for criterion in criteria:
        score = pattern[criterion.name]
        for sub in criterion.subcriteria:
            db.add(
                SubcriterionScore(
                    assessment_id=assessment.id,
                    subcriterion_id=sub.id,
                    selected_score=Decimal(score),
                    comments="The rating reflects a significant gap that needs a documented mitigation." if score <= 2 else "",
                )
            )
    for question in db.scalars(select(AssessmentQuestion).where(AssessmentQuestion.template_version_id == assessment.template_version_id, AssessmentQuestion.is_mandatory.is_(True))).all():
        db.add(QuestionResponse(assessment_id=assessment.id, question_id=question.id, response_text="Sample response captured for the demonstration record."))
    db.flush()
    recalculate(db, assessment)
    submit_assessment(db, bd, assessment)
    record_review(db, users["functional@diyar.local"], assessment.id, "functional_review", "confirmed", "Functional review confirms the scored position.")
    record_review(db, users["commercial@diyar.local"], assessment.id, "commercial_review", "confirmed", "Commercial review confirms the recorded assumptions.")
    if target == "awaiting":
        return
    decision = "rejected" if target == "rejected" else "approved"
    record_decision(
        db,
        users["executive@diyar.local"],
        assessment.id,
        DecisionIn(decision=decision, comments="Sample executive decision recorded through the approval workflow."),
    )
    if target == "won":
        transition_opportunity(db, bd, opportunity, "submitted")
        transition_opportunity(db, bd, opportunity, "won")
    elif target == "lost":
        transition_opportunity(db, bd, opportunity, "submitted")
        transition_opportunity(db, bd, opportunity, "lost")
