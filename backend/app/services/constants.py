OPPORTUNITY_SOURCES = [
    "Existing Client",
    "New Client",
    "Government Tender",
    "Strategic Partnership",
    "Referral",
    "Direct Business Development",
    "Other",
]

OPPORTUNITY_STATUSES = [
    "identified",
    "under_qualification",
    "under_assessment",
    "under_review",
    "awaiting_executive_decision",
    "approved",
    "conditionally_approved",
    "on_hold",
    "rejected",
    "submitted",
    "won",
    "lost",
    "cancelled",
]

MANUAL_TRANSITIONS = {
    "identified": {"under_qualification", "cancelled"},
    "under_qualification": {"under_assessment", "on_hold", "cancelled"},
    "under_assessment": {"on_hold"},
    "under_review": set(),
    "awaiting_executive_decision": set(),
    "approved": {"submitted", "on_hold", "cancelled"},
    "conditionally_approved": {"submitted", "on_hold", "cancelled"},
    "on_hold": {"under_qualification", "under_assessment", "cancelled"},
    "rejected": set(),
    "submitted": {"won", "lost"},
    "won": set(),
    "lost": set(),
    "cancelled": set(),
}

STRATEGIC_IMPORTANCE = ["low", "medium", "high", "critical"]

RISK_CATEGORIES = ["Financial", "Technical", "Operational", "Legal", "Reputational"]
RISK_STATUSES = ["open", "mitigated", "accepted", "closed"]

ACTION_STATUSES = ["not_started", "in_progress", "pending_validation", "completed", "cancelled"]
ACTION_PRIORITIES = ["low", "medium", "high", "critical"]

PARTNER_STATUSES = ["prospect", "active", "inactive", "suspended"]
NDA_STATUSES = ["not_started", "in_progress", "executed", "expired"]
AGREEMENT_STATUSES = ["none", "in_negotiation", "executed", "expired"]
COMMITMENT_STATUSES = ["proposed", "confirmed", "contracted", "withdrawn"]

RESOURCE_TYPES = ["internal", "external"]
AVAILABILITY_STATUSES = ["available", "partial", "gap", "unconfirmed"]

QUESTION_TYPES = [
    "single_choice",
    "multiple_choice",
    "numeric",
    "percentage",
    "yes_no",
    "short_text",
    "long_text",
    "document",
    "evidence_reference",
]

DECISION_VALUES = ["approved", "conditionally_approved", "on_hold", "rejected", "returned"]

EDITABLE_ASSESSMENT_STATUSES = {"draft", "in_progress", "returned"}

CONFIRMED_PARTNER_STATUSES = {"confirmed", "contracted"}

PERMISSIONS = [
    ("admin.full", "Full administration. Approval rights follow the admin_can_approve setting."),
    ("users.manage", "Manage users and role assignments"),
    ("config.manage", "Configure assessment templates, scales, and thresholds"),
    ("opportunities.create", "Register opportunities"),
    ("opportunities.edit_own", "Edit opportunities owned by the user"),
    ("opportunities.edit_any", "Edit any opportunity"),
    ("opportunities.view_all", "View the full opportunity portfolio"),
    ("opportunities.view_assigned", "View owned or assigned opportunities"),
    ("assessments.complete_any", "Score any assessment"),
    ("assessments.complete_assigned", "Score assigned assessment sections"),
    ("assessments.review", "Validate assessments during functional or commercial review"),
    ("commercial.edit", "Edit commercial feasibility inputs"),
    ("approvals.decide", "Record executive approval decisions"),
    ("dashboard.view", "View the executive dashboard"),
    ("audit.view", "View the audit log"),
    ("partners.manage", "Create and update partner records"),
    ("reports.export", "Generate and export reports"),
]

ROLE_PERMISSIONS = {
    "System Administrator": [
        "admin.full",
        "users.manage",
        "config.manage",
        "audit.view",
        "dashboard.view",
        "reports.export",
        "opportunities.view_all",
        "partners.manage",
    ],
    "Business Development Manager": [
        "opportunities.create",
        "opportunities.edit_own",
        "opportunities.view_all",
        "assessments.complete_any",
        "commercial.edit",
        "dashboard.view",
        "partners.manage",
        "reports.export",
    ],
    "Assessment Evaluator": [
        "opportunities.view_assigned",
        "assessments.complete_assigned",
        "dashboard.view",
    ],
    "Functional Reviewer": [
        "assessments.review",
        "opportunities.view_all",
        "dashboard.view",
        "reports.export",
    ],
    "Commercial Reviewer": [
        "assessments.review",
        "commercial.edit",
        "opportunities.view_all",
        "dashboard.view",
        "reports.export",
    ],
    "Executive Approver": [
        "approvals.decide",
        "opportunities.view_all",
        "dashboard.view",
        "audit.view",
        "reports.export",
    ],
    "Executive Viewer": [
        "opportunities.view_all",
        "dashboard.view",
        "reports.export",
    ],
}

ROLE_DESCRIPTIONS = {
    "System Administrator": "Full application administration. Executive approval can be enabled separately.",
    "Business Development Manager": "Registers and maintains opportunities and initiates assessments.",
    "Assessment Evaluator": "Completes assigned assessment sections with scores and evidence.",
    "Functional Reviewer": "Validates technical and operational feasibility.",
    "Commercial Reviewer": "Validates commercial assumptions, cost, and margin.",
    "Executive Approver": "Approves, rejects, returns, or overrides recommendations.",
    "Executive Viewer": "Read-only access to the portfolio, approved assessments, and reports.",
}

DEFAULT_SCALE = [
    (5, "Excellent", "Fully meets expectations", False, False),
    (4, "Good", "Meets most expectations", False, False),
    (3, "Average", "Partially meets expectations", False, False),
    (2, "Weak", "Significant gaps", True, True),
    (1, "Poor", "Does not meet expectations", True, True),
]

DEFAULT_RULES = [
    ("Proceed with the opportunity", 85, 100, "The opportunity meets Diyar's threshold to proceed.", "Approve pursuit and mobilise the bid team.", "#0F766E", 1),
    ("Proceed subject to closing identified gaps", 70, 84.99, "The opportunity is attractive if identified gaps are closed before commitment.", "Approve conditionally and track mandatory gap-closure actions.", "#1B4F8A", 2),
    ("Limit commitment and conduct further due diligence", 55, 69.99, "Material uncertainty remains. Limit exposure until further diligence is complete.", "Limit spend and commission the outstanding diligence.", "#B45309", 3),
    ("Reconsider scope, partnership or commercial model", 40, 54.99, "The current shape of the opportunity is not strong enough to commit.", "Reconsider scope, partner model, or commercial terms before any further pursuit.", "#C2410C", 4),
    ("Do not commit under current conditions", 0, 39.99, "The opportunity does not meet Diyar's conditions for commitment.", "Decline or stop pursuit under the current conditions.", "#B91C1C", 5),
]

DEFAULT_CRITERIA = [
    (
        "Strategic Business Value",
        "How strongly the opportunity advances Diyar's strategy, market position, and long-term client relationships.",
        15,
        [
            ("Alignment with Diyar strategy", 40, "Fit with stated strategic priorities."),
            ("Market positioning", 30, "Effect on Diyar's position in the target market."),
            ("Long-term relationship value", 30, "Value of the client relationship beyond this contract."),
        ],
    ),
    (
        "Client Opportunity & Probability of Winning",
        "Strength of the client opportunity and Diyar's realistic probability of being selected.",
        10,
        [
            ("Client relationship strength", 35, "Depth and quality of the current relationship."),
            ("Competitive position", 35, "Position relative to known competitors."),
            ("Probability of award", 30, "Evidence supporting the likelihood of award."),
        ],
    ),
    (
        "Technical Delivery Capability",
        "Diyar's ability to deliver the required technical scope to the client's standard.",
        20,
        [
            ("Relevant technical expertise", 25, "Depth of directly relevant expertise."),
            ("Previous implementation experience", 20, "Comparable deliveries already completed."),
            ("Technology availability", 15, "Access to the required technology and platforms."),
            ("Integration complexity", 15, "Complexity of integrating with the client environment. A higher score means complexity is manageable."),
            ("Compliance with client requirements", 15, "Coverage of stated functional and regulatory requirements."),
            ("Technical timeline feasibility", 10, "Whether the technical plan fits the expected timeline."),
        ],
    ),
    (
        "Partner Credibility & Commitment",
        "Whether required partners are credible, capable, and committed.",
        15,
        [
            ("Partner track record", 30, "Evidence of relevant partner delivery."),
            ("Commitment confirmation", 35, "How firmly the partner is committed to this pursuit."),
            ("Capability fit", 35, "Fit between partner capabilities and the scope."),
        ],
    ),
    (
        "Commercial Attractiveness",
        "Revenue quality, margin, and the commercial terms Diyar would accept.",
        20,
        [
            ("Margin attractiveness", 40, "Expected margin relative to Diyar's hurdle."),
            ("Payment and commercial terms", 30, "Acceptability of payment, liability, and commercial terms."),
            ("Revenue quality", 30, "Quality, timing, and repeatability of the revenue."),
        ],
    ),
    (
        "Resource Availability & Delivery Feasibility",
        "Whether Diyar can staff and deliver the work without an unmanageable gap.",
        10,
        [
            ("Internal capacity", 40, "Availability of internal people for the expected window."),
            ("Critical skills coverage", 35, "Coverage of skills that the delivery cannot proceed without."),
            ("Timeline feasibility", 25, "Whether staffing can meet the client timeline."),
        ],
    ),
    (
        "Risk Management",
        "Quality of risk identification and the readiness of mitigation before commitment.",
        10,
        [
            ("Risk identification quality", 30, "Whether material risks are known and described."),
            ("Mitigation readiness", 40, "Whether mitigations are owned and actionable."),
            ("Residual exposure", 30, "Acceptability of risk remaining after mitigation. A higher score means lower residual exposure."),
        ],
    ),
]
