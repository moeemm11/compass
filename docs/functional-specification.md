DIYAR COMPASS
Functional & Technical Specification
Product: Executive Decision Intelligence & Opportunity Assessment Platform Document Version: 1.0 Status: Development Baseline Classification: Internal – Diyar Target Development Environment: Cursor AI

1. Executive Summary
1.1 Purpose
DIYAR COMPASS is an internal enterprise application designed to support Diyar's executive management in evaluating, qualifying, prioritizing and approving business opportunities.
The platform will provide a standardized, configurable and evidence-based framework for assessing opportunities before Diyar commits commercial, technical, operational or financial resources.
The application will combine:
	•	Opportunity management.
	•	Configurable assessment methodologies.
	•	Weighted scoring and recommendation engine.
	•	Commercial feasibility analysis.
	•	Risk and feasibility assessment.
	•	Partner and capability management.
	•	Resource availability assessment.
	•	Executive approval workflows.
	•	Portfolio analytics.
	•	Historical decision intelligence.
	•	AI-assisted executive advisory capabilities (future phase).
1.2 Business Objectives
The primary objectives are:
	•	Standardize opportunity assessment across Diyar.
	•	Improve the quality and consistency of executive decisions.
	•	Establish objective criteria for Bid / No-Bid decisions.
	•	Identify commercial, technical and operational gaps before commitment.
	•	Evaluate strategic partnerships and delivery models.
	•	Improve visibility of the business development pipeline.
	•	Maintain an auditable history of management decisions.
	•	Support future expansion into broader business governance and investment assessments.
1.3 Guiding Principles
The application must follow these principles:
	•	Configuration over hardcoding.
	•	Evidence-based assessment.
	•	Explainable scoring.
	•	Separation between recommendation and management decision.
	•	Full auditability.
	•	Historical assessment preservation.
	•	Modular and extensible architecture.
	•	Human approval for consequential business decisions.

2. Scope
2.1 MVP Scope
The first release will include:
Module
Functionality
Authentication
User login and access management
User Management
Users, roles and permissions
Executive Dashboard
Opportunity portfolio overview
Opportunity Management
Create, update and track opportunities
Assessment Configuration
Criteria, weights, scales and thresholds
Assessment Engine
Evaluate criteria and calculate scores
Recommendation Engine
Generate management recommendations
Risk Management
Identify and assess risks
Commercial Assessment
Basic financial feasibility
Partner Management
Maintain partner profiles and capabilities
Approval Workflow
Executive review and decision recording
Reporting
PDF and printable assessment reports
Audit Trail
Record significant application activities
2.2 Future Scope
The following capabilities should be accommodated by the architecture but do not need to be implemented in the first release:
	•	AI Executive Advisor.
	•	Automated RFP and proposal analysis.
	•	AI-assisted scoring suggestions.
	•	Scenario simulation.
	•	Advanced resource capacity planning.
	•	Market intelligence integration.
	•	Historical win/loss analysis.
	•	Partner-to-opportunity matching.
	•	Multiple assessment templates.
	•	Strategic investment evaluation.

3. User Roles and Access Management
The application must implement Role-Based Access Control (RBAC).
3.1 User Roles
A. System Administrator
Full application administration.
Responsibilities:
	•	Manage users.
	•	Configure roles and permissions.
	•	Configure assessment templates.
	•	Manage scoring scales.
	•	Configure recommendation thresholds.
	•	Configure system settings.
	•	View audit logs.
B. Business Development Manager
Responsibilities:
	•	Create opportunities.
	•	Maintain opportunity information.
	•	Initiate assessments.
	•	Assign assessment owners.
	•	Upload supporting documents.
	•	Track opportunity status.
C. Assessment Evaluator
Responsibilities:
	•	Complete assigned assessment sections.
	•	Enter criterion scores.
	•	Provide justifications.
	•	Upload evidence.
	•	Identify risks and gaps.
D. Functional Reviewer
Responsibilities:
	•	Review technical and operational assessments.
	•	Validate scoring.
	•	Provide comments.
	•	Request additional information.
	•	Confirm delivery feasibility.
E. Commercial Reviewer
Responsibilities:
	•	Review commercial assumptions.
	•	Validate estimated costs and margins.
	•	Assess commercial attractiveness.
	•	Review financial exposure.
F. Executive Approver
Responsibilities:
	•	Review completed assessments.
	•	View recommendations.
	•	Approve or reject opportunities.
	•	Request reassessment.
	•	Override system recommendations with justification.
G. Executive Viewer
Read-only access to dashboards, approved assessments and reports.
3.2 Permissions Matrix
Function
Admin
BD Manager
Evaluator
Reviewer
Executive
Manage users
Yes
No
No
No
No
Configure scoring
Yes
No
No
No
No
Create opportunity
Yes
Yes
No
No
No
Edit opportunity
Yes
Owner
No
No
No
Complete assessment
Yes
Yes
Assigned
Review
No
Review assessment
Yes
No
No
Yes
Yes
Approve opportunity
Yes*
No
No
No
Yes
View dashboard
Yes
Yes
Assigned
Yes
Yes
View audit logs
Yes
No
No
No
Read-only
*Administrative approval rights should be configurable separately from system administration.

4. Functional Requirements
4.1 Executive Dashboard
The dashboard is the landing page after authentication.
It must provide a consolidated view of Diyar's business opportunity portfolio.
4.1.1 KPI Cards
Display:
	•	Total opportunities.
	•	Opportunities under assessment.
	•	Opportunities awaiting approval.
	•	Opportunities approved to proceed.
	•	Opportunities conditionally approved.
	•	Opportunities rejected.
	•	Total estimated pipeline value.
	•	Risk-adjusted pipeline value.
	•	Average opportunity assessment score.
4.1.2 Dashboard Charts
Include:
	•	Opportunities by status.
	•	Opportunities by recommendation.
	•	Opportunities by country.
	•	Opportunities by service line.
	•	Opportunity pipeline by financial value.
	•	Average assessment scores over time.
	•	Opportunities by business development owner.
	•	Win/loss distribution (once outcome data becomes available).
4.1.3 Dashboard Filters
	•	Date range.
	•	Country.
	•	Business unit.
	•	Service line.
	•	Opportunity status.
	•	Opportunity owner.
	•	Partner.
	•	Recommendation category.
4.1.4 Recent Activities
Display:
	•	Recently created opportunities.
	•	Recently submitted assessments.
	•	Pending executive approvals.
	•	Recent management decisions.
	•	Upcoming action deadlines.

4.2 Opportunity Management
4.2.1 Create Opportunity
Users with the appropriate permissions can register a new opportunity.
Required Fields
Field
Type
Mandatory
Opportunity Reference
Auto-generated
Yes
Opportunity Name
Text
Yes
Client Name
Text / Client reference
Yes
Country
Dropdown
Yes
Sector
Dropdown
Yes
Opportunity Description
Long text
Yes
Service Line
Multi-select
Yes
Opportunity Source
Dropdown
Yes
Estimated Contract Value
Decimal
No
Currency
Dropdown
Yes
Expected Award Date
Date
No
Expected Start Date
Date
No
Expected Duration
Number
No
Business Development Owner
User reference
Yes
Opportunity Status
System controlled
Yes
Strategic Importance
Dropdown
No
Opportunity Source Values
	•	Existing Client.
	•	New Client.
	•	Government Tender.
	•	Strategic Partnership.
	•	Referral.
	•	Direct Business Development.
	•	Other.
Opportunity Status Lifecycle
	•	Identified.
	•	Under Qualification.
	•	Under Assessment.
	•	Under Review.
	•	Awaiting Executive Decision.
	•	Approved.
	•	Conditionally Approved.
	•	On Hold.
	•	Rejected.
	•	Submitted.
	•	Won.
	•	Lost.
	•	Cancelled.
Status transitions must be controlled by workflow rules.
4.2.2 Opportunity Details
Each opportunity must have a dedicated workspace with tabs:
	•	Overview.
	•	Assessment.
	•	Commercial.
	•	Partners.
	•	Risks.
	•	Resources.
	•	Documents.
	•	Action Plan.
	•	Management Decisions.
	•	Activity History.

4.3 Assessment Configuration Engine
This module is one of the most important components of COMPASS.
It must allow administrators to create and maintain assessment methodologies without modifying application code.
4.3.1 Assessment Templates
Administrators can create multiple assessment templates.
Examples:
	•	Standard Opportunity Assessment.
	•	Strategic Partnership Assessment.
	•	Bid / No-Bid Assessment.
	•	Project Feasibility Assessment.
	•	New Service Offering Assessment.
Each template contains:
	•	Template name.
	•	Description.
	•	Version.
	•	Status.
	•	Effective date.
	•	Evaluation categories.
	•	Subcriteria.
	•	Scoring methodology.
	•	Recommendation rules.
	•	Mandatory questions.
4.3.2 Default Opportunity Assessment Template
The initial template must include seven evaluation criteria.
Criterion
Weight
Strategic Business Value
15%
Client Opportunity & Probability of Winning
10%
Technical Delivery Capability
20%
Partner Credibility & Commitment
15%
Commercial Attractiveness
20%
Resource Availability & Delivery Feasibility
10%
Risk Management
10%
Total
100%
Weights must be configurable.
System validation must ensure that the sum of active criterion weights equals 100% before publishing a template.
4.3.3 Subcriteria
Each main criterion can contain multiple subcriteria.
Example:
Technical Delivery Capability – 20%
Subcriterion
Internal Weight
Relevant technical expertise
25%
Previous implementation experience
20%
Technology availability
15%
Integration complexity
15%
Compliance with client requirements
15%
Technical timeline feasibility
10%
Total
100%
The subcriterion weights are relative to the parent criterion.
Administrators must be able to:
	•	Add subcriteria.
	•	Edit descriptions.
	•	Change weights.
	•	Activate/deactivate subcriteria.
	•	Define mandatory responses.
	•	Define scoring guidance.
4.3.4 Scoring Scale Configuration
The system must support configurable scoring scales.
Default scale:
Score
Rating
Guidance
5
Excellent
Fully meets expectations
4
Good
Meets most expectations
3
Average
Partially meets expectations
2
Weak
Significant gaps
1
Poor
Does not meet expectations
The administrator must be able to define:
	•	Numeric score.
	•	Rating label.
	•	Description.
	•	Minimum and maximum values.
	•	Whether a value is selectable.
	•	Whether a rating requires mandatory justification.
The application must not hardcode the five-level scale.
4.3.5 Assessment Questions
Each criterion/subcriterion can contain configurable assessment questions.
Question types:
	•	Single choice.
	•	Multiple choice.
	•	Numeric.
	•	Percentage.
	•	Yes / No.
	•	Short text.
	•	Long text.
	•	Document attachment.
	•	Evidence reference.
Conditional question activation should be supported in a future release.

4.4 Assessment Execution
4.4.1 Assessment Workflow
	•	Business Development Manager creates the opportunity.
	•	User selects an assessment template.
	•	System creates an assessment instance using the published template version.
	•	Assessment is assigned to evaluators.
	•	Evaluators complete their assigned sections.
	•	Evaluators enter scores and supporting justifications.
	•	System calculates criterion and overall scores.
	•	Assessment is submitted for review.
	•	Reviewers validate and comment.
	•	Assessment proceeds to executive approval.
4.4.2 Assessment Screen
Each assessment must display:
	•	Criterion name.
	•	Criterion description.
	•	Weight.
	•	Subcriteria.
	•	Available scoring values.
	•	Selected rating.
	•	Weighted result.
	•	Evaluation comments.
	•	Evidence attachments.
	•	Identified gaps.
	•	Assigned evaluator.
	•	Completion status.
4.4.3 Mandatory Validation
The system must prevent submission when:
	•	Mandatory criteria are incomplete.
	•	Required comments are missing.
	•	Mandatory evidence is missing.
	•	Criterion weights are invalid.
	•	Assessment is based on an unpublished or invalid template.
An incomplete assessment must not receive a final management recommendation.

4.5 Weighted Scoring Engine
4.5.1 Calculation Logic
Each criterion is scored based on the selected rating.
Formula:
Weighted Criterion Score = (Selected Score / Maximum Score) × Criterion Weight
Overall Assessment Score:
Overall Score = Sum of all Weighted Criterion Scores.
For the default five-level scale, the resulting score is between 0 and 100.
Example:
Criterion
Weight
Score
Weighted Result
Strategic Business Value
15%
5/5
15
Client Opportunity
10%
4/5
8
Technical Capability
20%
3/5
12
Partner Credibility
15%
4/5
12
Commercial Attractiveness
20%
4/5
16
Resource Availability
10%
3/5
6
Risk Management
10%
4/5
8
Total
100%

77
The result must be displayed on a 0–100 scale.
4.5.2 Subcriterion Calculation
When subcriteria exist:
Parent Criterion Score = Sum of (Subcriterion Normalized Score × Subcriterion Weight).
The parent score is then multiplied by the parent criterion weight.
4.5.3 Missing Scores
For MVP:
	•	Missing mandatory scores prevent final submission.
	•	Draft assessments may contain incomplete scores.
	•	Do not automatically treat missing scores as zero.
	•	Do not redistribute weights among completed criteria.
	•	Show completion percentage separately from the calculated score.
4.5.4 Rounding
Calculations must use full precision internally.
Display scores rounded to two decimal places.
Recommendation thresholds must use the unrounded calculated score.

4.6 Recommendation Engine
The recommendation engine must map the overall assessment score to a configurable recommendation.
Default thresholds:
Score
Recommendation
85–100
Proceed with the opportunity
70–84.99
Proceed subject to closing identified gaps
55–69.99
Limit commitment and conduct further due diligence
40–54.99
Reconsider scope, partnership or commercial model
0–39.99
Do not commit under current conditions
Administrators can configure:
	•	Minimum score.
	•	Maximum score.
	•	Recommendation name.
	•	Recommendation description.
	•	Recommended management action.
	•	Display color.
	•	Priority.
The threshold ranges must be continuous, non-overlapping and cover 0–100.
4.6.1 Automatic Recommendation
The system generates the recommendation based on the final score.
4.6.2 Management Override
An executive approver can override the system recommendation.
Mandatory override fields:
	•	Original recommendation.
	•	Selected management decision.
	•	Override justification.
	•	Decision maker.
	•	Decision timestamp.
Both the original recommendation and final decision must remain visible.
4.6.3 Critical Red Flags
Critical risks can trigger mandatory escalation.
Example conditions:
	•	No confirmed delivery partner when a partner is mandatory.
	•	Unacceptable contractual risk.
	•	Negative expected gross margin.
	•	Critical resource gap.
	•	Mandatory regulatory requirement not satisfied.
Red flags must be configurable and must not silently change the mathematical score.
An executive can approve an exception only with a recorded justification and the required authority.

4.7 Risk Management
Each opportunity must have a risk register.
Risk fields:
Field
Description
Risk Reference
Auto-generated
Risk Title
Short description
Risk Category
Financial, Technical, Operational, Legal, Reputational
Description
Detailed explanation
Probability
1–5
Impact
1–5
Inherent Risk Score
Probability × Impact
Mitigation Plan
Planned actions
Risk Owner
Assigned user
Target Date
Mitigation deadline
Residual Probability
1–5
Residual Impact
1–5
Residual Risk Score
Probability × Impact
Status
Open, Mitigated, Accepted, Closed
The system must provide a 5×5 risk heatmap.
Risk records must be linked to the opportunity and optionally to assessment criteria.

4.8 Commercial Assessment
The commercial module provides a financial feasibility assessment.
4.8.1 Financial Inputs
	•	Estimated contract value.
	•	Currency.
	•	Internal delivery cost.
	•	Partner cost.
	•	Travel and accommodation.
	•	Third-party expenses.
	•	Licensing costs.
	•	Other operational expenses.
	•	Bid preparation cost.
	•	Contingency.
	•	Expected probability of winning.
4.8.2 Calculations
Total Estimated Cost = Sum of all delivery and operational costs.
Gross Profit = Contract Value - Total Estimated Cost.
Gross Margin (%) = Gross Profit / Contract Value × 100.
Expected Revenue = Contract Value × Probability of Winning.
Expected Contribution = Expected Revenue - (Total Estimated Cost × Probability of Winning) - Bid Preparation Cost.
The application must clearly label assumptions and distinguish estimated values from confirmed commercial figures.
4.8.3 Commercial Dashboard
Display:
	•	Contract value.
	•	Estimated cost.
	•	Gross profit.
	•	Gross margin.
	•	Expected revenue.
	•	Expected contribution.
	•	Partner cost percentage.
	•	Bid preparation investment.
Financial calculations must account for currency consistency. Currency conversion rates, if introduced, must retain their source and effective date.

4.9 Partner Management
Maintain a centralized partner database.
Partner information:
	•	Company name.
	•	Country.
	•	Company description.
	•	Website.
	•	Contact information.
	•	Industry.
	•	Healthcare capabilities.
	•	Technology capabilities.
	•	Certifications.
	•	Project references.
	•	Relevant experience.
	•	Available consultants.
	•	Partnership status.
	•	NDA status.
	•	Agreement status.
	•	Commercial arrangements.
	•	Internal relationship owner.
	•	Performance history.
Partner capability categories should be configurable.
Examples:
	•	SAP Healthcare.
	•	HIS / EHR.
	•	Digital Health.
	•	HIMSS EMRAM.
	•	Healthcare Advisory.
	•	Clinical Informatics.
	•	AI and Analytics.
	•	Integration and Interoperability.
	•	Cybersecurity.
Each opportunity can be associated with one or more partners.

4.10 Resource Feasibility
For each opportunity, allow users to identify required roles.
Resource fields:
	•	Role.
	•	Required skills.
	•	Number of resources.
	•	Estimated allocation percentage.
	•	Estimated duration.
	•	Internal/external resource.
	•	Availability status.
	•	Resource owner.
	•	Identified gap.
The system should summarize:
	•	Total resource demand.
	•	Confirmed internal availability.
	•	External resource dependency.
	•	Critical skill gaps.
	•	Delivery feasibility status.
Actual calendar-based capacity integration can be introduced in a later release.

4.11 Action Plan and Gap Management
Every assessment must support an action plan.
Fields:
	•	Action reference.
	•	Identified gap.
	•	Related criterion.
	•	Required action.
	•	Assigned owner.
	•	Priority.
	•	Target date.
	•	Status.
	•	Completion notes.
	•	Supporting documents.
Action statuses:
	•	Not Started.
	•	In Progress.
	•	Pending Validation.
	•	Completed.
	•	Cancelled.
For conditional approval, management can specify mandatory actions that must be closed before commercial or delivery commitment.

4.12 Approval Workflow
The system must support configurable approval stages.
Default workflow:
Opportunity Registration → Assessment → Functional Review → Commercial Review → Executive Approval → Final Decision.
Decision values:
	•	Approved.
	•	Conditionally Approved.
	•	On Hold.
	•	Rejected.
	•	Returned for Reassessment.
Approval records must include:
	•	Approver.
	•	Decision.
	•	Comments.
	•	Timestamp.
	•	Previous status.
	•	New status.
The system must preserve the full approval history.

4.13 Reporting
The system must support:
A. Executive Assessment Report
Include:
	•	Opportunity overview.
	•	Client and market information.
	•	Strategic rationale.
	•	Assessment criteria and weights.
	•	Individual scores.
	•	Overall score.
	•	Recommendation.
	•	Identified strengths.
	•	Identified gaps.
	•	Risk assessment.
	•	Commercial feasibility.
	•	Partner and resource readiness.
	•	Required actions.
	•	Management decision.
	•	Approval history.
B. Opportunity Portfolio Report
Include:
	•	Total opportunity count.
	•	Pipeline value.
	•	Opportunities by recommendation.
	•	Opportunities by country.
	•	Opportunities by service line.
	•	Average scores.
	•	Opportunity status.
C. Assessment Comparison Report
Compare two or more opportunities using the same assessment template and version.
Reports must be exportable to PDF.

5. Database Design
The application must use PostgreSQL with relational data integrity.
5.1 Core Tables
User and Access Management
users
	•	id (UUID, PK)
	•	full_name
	•	email
	•	password_hash / external_identity_reference
	•	is_active
	•	created_at
	•	updated_at
roles
	•	id
	•	name
	•	description
permissions
	•	id
	•	code
	•	description
user_roles
	•	user_id
	•	role_id
role_permissions
	•	role_id
	•	permission_id
Opportunity Management
opportunities
	•	id
	•	reference_number
	•	name
	•	client_name
	•	country
	•	sector
	•	description
	•	opportunity_source
	•	estimated_value
	•	currency
	•	expected_award_date
	•	expected_start_date
	•	expected_duration
	•	owner_id
	•	status
	•	created_at
	•	updated_at
Assessment Configuration
assessment_templates
	•	id
	•	name
	•	description
	•	template_type
	•	status
	•	current_version_id
	•	created_by
assessment_template_versions
	•	id
	•	template_id
	•	version_number
	•	status
	•	effective_from
	•	published_at
	•	created_at
evaluation_criteria
	•	id
	•	template_version_id
	•	name
	•	description
	•	weight
	•	display_order
	•	is_mandatory
	•	is_active
evaluation_subcriteria
	•	id
	•	criterion_id
	•	name
	•	description
	•	weight
	•	display_order
	•	is_mandatory
scoring_scales
	•	id
	•	template_version_id
	•	name
	•	minimum_value
	•	maximum_value
scoring_scale_values
	•	id
	•	scoring_scale_id
	•	numeric_value
	•	label
	•	description
	•	display_order
recommendation_rules
	•	id
	•	template_version_id
	•	recommendation_name
	•	minimum_score
	•	maximum_score
	•	description
	•	management_action
	•	color
Assessment Execution
assessments
	•	id
	•	opportunity_id
	•	template_version_id
	•	assessment_number
	•	status
	•	completion_percentage
	•	calculated_score
	•	recommendation
	•	submitted_by
	•	submitted_at
	•	created_at
criterion_scores
	•	id
	•	assessment_id
	•	criterion_id
	•	selected_score
	•	normalized_score
	•	weighted_score
	•	comments
	•	evaluator_id
	•	evaluated_at
subcriterion_scores
	•	id
	•	assessment_id
	•	subcriterion_id
	•	selected_score
	•	comments
	•	evaluator_id
assessment_evidence
	•	id
	•	assessment_id
	•	criterion_score_id
	•	file_name
	•	storage_key
	•	uploaded_by
	•	uploaded_at
Risk Management
risks
	•	id
	•	opportunity_id
	•	title
	•	description
	•	category
	•	probability
	•	impact
	•	inherent_score
	•	residual_probability
	•	residual_impact
	•	residual_score
	•	mitigation_plan
	•	owner_id
	•	status
	•	due_date
Commercial Assessment
commercial_assessments
	•	id
	•	opportunity_id
	•	assessment_id
	•	contract_value
	•	currency
	•	internal_cost
	•	partner_cost
	•	operational_cost
	•	bid_cost
	•	contingency
	•	probability_of_winning
	•	gross_profit
	•	gross_margin
	•	expected_revenue
	•	expected_contribution
Partner Management
partners
	•	id
	•	name
	•	country
	•	description
	•	website
	•	status
	•	nda_status
	•	agreement_status
	•	relationship_owner_id
partner_capabilities
	•	id
	•	name
	•	description
partner_capability_mapping
	•	partner_id
	•	capability_id
	•	proficiency_level
	•	evidence_reference
opportunity_partners
	•	opportunity_id
	•	partner_id
	•	role
	•	commitment_status
	•	commercial_arrangement
Resource Planning
resource_requirements
	•	id
	•	opportunity_id
	•	role
	•	required_skills
	•	quantity
	•	allocation_percentage
	•	duration
	•	resource_type
	•	availability_status
Actions and Approvals
action_items
	•	id
	•	opportunity_id
	•	assessment_id
	•	title
	•	description
	•	owner_id
	•	priority
	•	due_date
	•	status
approval_records
	•	id
	•	opportunity_id
	•	assessment_id
	•	approver_id
	•	decision
	•	comments
	•	decided_at
management_decisions
	•	id
	•	opportunity_id
	•	assessment_id
	•	calculated_recommendation
	•	final_decision
	•	override_reason
	•	decision_maker_id
	•	decision_date
System Governance
audit_logs
	•	id
	•	user_id
	•	entity_type
	•	entity_id
	•	action
	•	old_values (JSONB)
	•	new_values (JSONB)
	•	created_at
attachments
	•	id
	•	entity_type
	•	entity_id
	•	original_file_name
	•	storage_key
	•	mime_type
	•	file_size
	•	uploaded_by
	•	uploaded_at
notifications
	•	id
	•	user_id
	•	title
	•	message
	•	notification_type
	•	is_read
	•	created_at
5.2 Database Design Principles
	•	Use UUID primary keys.
	•	Use foreign keys for relationships.
	•	Use created_at and updated_at timestamps.
	•	Use soft deletion for business records where appropriate.
	•	Preserve historical assessment records.
	•	Use JSONB only for flexible metadata and audit snapshots, not as a replacement for core relational structures.
	•	Store files outside the relational database.
	•	Use database transactions for assessment submission and management approval.

6. Technical Architecture
6.1 Architecture Overview
Adopt a modular monolith architecture for MVP.
This avoids unnecessary microservice complexity while preserving clear module boundaries.
Frontend
Next.js + React + TypeScript.
Responsibilities:
	•	UI rendering.
	•	Form management.
	•	Client-side validation.
	•	Dashboard visualization.
	•	API integration.
	•	Authentication state.
	•	Role-based navigation.
Recommended libraries:
	•	Tailwind CSS.
	•	shadcn/ui.
	•	React Hook Form.
	•	Zod.
	•	TanStack Query.
	•	Recharts.
	•	Lucide Icons.
Backend
Python + FastAPI.
Responsibilities:
	•	Business logic.
	•	Scoring calculations.
	•	Workflow management.
	•	Access control.
	•	Validation.
	•	Database operations.
	•	Reporting.
	•	Audit logging.
Recommended libraries:
	•	SQLAlchemy.
	•	Alembic.
	•	Pydantic.
	•	PostgreSQL driver.
	•	JWT authentication or a suitable OIDC integration.
	•	ReportLab for PDF generation.
Database
PostgreSQL.
File Storage
Use an S3-compatible object storage service or private file storage for the initial deployment.
Deployment
Docker and Docker Compose for development.
Production deployment can use:
	•	Internal virtual machines.
	•	Private cloud.
	•	Approved cloud infrastructure.

7. Backend API Specification
Base URL:
/api/v1
7.1 Authentication
Method
Endpoint
Description
POST
/auth/login
Authenticate
POST
/auth/refresh
Refresh session
POST
/auth/logout
Logout
GET
/auth/me
Current user
7.2 Opportunities
Method
Endpoint
Description
GET
/opportunities
List opportunities
POST
/opportunities
Create opportunity
GET
/opportunities/{id}
Get opportunity
PUT
/opportunities/{id}
Update opportunity
DELETE
/opportunities/{id}
Archive opportunity
GET
/opportunities/{id}/history
Activity history
7.3 Assessment Configuration
Method
Endpoint
Description
GET
/assessment-templates
List templates
POST
/assessment-templates
Create template
GET
/assessment-templates/{id}
Get template
PUT
/assessment-templates/{id}
Update draft
POST
/assessment-templates/{id}/publish
Publish version
GET
/assessment-templates/{id}/versions
Version history
7.4 Assessments
Method
Endpoint
Description
GET
/assessments
List assessments
POST
/assessments
Create assessment
GET
/assessments/{id}
Get assessment
PUT
/assessments/{id}
Update draft
POST
/assessments/{id}/submit
Submit assessment
POST
/assessments/{id}/recalculate
Recalculate scores
GET
/assessments/{id}/result
Get calculated result
7.5 Risk Management
Method
Endpoint
Description
GET
/opportunities/{id}/risks
List risks
POST
/opportunities/{id}/risks
Create risk
PUT
/risks/{id}
Update risk
DELETE
/risks/{id}
Archive risk
7.6 Commercial Assessment
Method
Endpoint
Description
GET
/opportunities/{id}/commercial
Get commercial assessment
POST
/opportunities/{id}/commercial
Create assessment
PUT
/commercial/{id}
Update assessment
7.7 Approvals
Method
Endpoint
Description
GET
/approvals/pending
Pending approvals
POST
/assessments/{id}/approve
Approve
POST
/assessments/{id}/reject
Reject
POST
/assessments/{id}/return
Request reassessment
7.8 Reporting
Method
Endpoint
Description
GET
/reports/dashboard
Dashboard data
GET
/reports/opportunities
Portfolio report
GET
/reports/assessment/{id}
Assessment report
GET
/reports/assessment/{id}/pdf
Generate PDF
API responses must follow a consistent structure, use appropriate HTTP status codes and provide clear validation errors.
All endpoints must enforce server-side permissions.

8. UI/UX Specification
8.1 Branding
Product name: DIYAR COMPASS.
Suggested tagline:
"Navigate Opportunities. Make Informed Decisions."
Visual identity:
	•	Primary: Deep navy blue.
	•	Secondary: Professional blue.
	•	Accent: Teal.
	•	Background: Light neutral.
	•	Success: Green.
	•	Warning: Amber.
	•	Critical: Red.
The UI should be modern, minimal, enterprise-oriented and suitable for executive presentations.
8.2 Main Navigation
	•	Executive Dashboard.
	•	Opportunities.
	•	Assessments.
	•	Partners.
	•	Commercial.
	•	Risk Management.
	•	Resources.
	•	Reports.
	•	Administration.
The AI Executive Advisor can be introduced as a separate navigation item in a future release.
8.3 Main Screens
The MVP must implement:
	•	Login screen.
	•	Executive dashboard.
	•	Opportunity listing.
	•	Opportunity creation.
	•	Opportunity detail workspace.
	•	Assessment template administration.
	•	Criteria and subcriteria configuration.
	•	Scoring scale configuration.
	•	Recommendation threshold configuration.
	•	Assessment execution.
	•	Assessment results.
	•	Risk register.
	•	Commercial assessment.
	•	Partner listing and details.
	•	Approval inbox.
	•	Executive decision screen.
	•	PDF report preview.
	•	User and role administration.
	•	Audit log viewer.
8.4 UI Behavior
	•	Responsive desktop-first layout.
	•	Consistent navigation.
	•	Search and filtering.
	•	Pagination for large lists.
	•	Loading and error states.
	•	Confirmation before destructive operations.
	•	Clear status indicators.
	•	Validation messages.
	•	Accessible forms.
	•	No reliance on color alone to communicate status.

9. Security and Audit Requirements
The application will contain commercially sensitive internal information.
Security requirements:
	•	Authentication required for all protected application functions.
	•	Server-side RBAC enforcement.
	•	Secure password hashing when local authentication is used.
	•	HTTPS in production.
	•	Secure session and token management.
	•	Protection against SQL injection.
	•	Input validation and output encoding.
	•	File upload validation.
	•	File access authorization.
	•	Audit logging for important actions.
	•	Environment-based secrets management.
	•	Database backup and recovery procedures.
	•	Configurable session expiration.
	•	Protection against unauthorized assessment modifications.
Audit events should include:
	•	Opportunity creation and changes.
	•	Assessment submission.
	•	Score changes.
	•	Template publication.
	•	Weight changes.
	•	Recommendation changes.
	•	Management overrides.
	•	Approval decisions.
	•	User and permission changes.
Historical audit records must not be editable through the normal application interface.

10. Configuration and Version Management
This is a critical technical requirement.
Published assessment templates must be immutable.
When an administrator changes:
	•	Criteria.
	•	Weights.
	•	Subcriteria.
	•	Scoring scales.
	•	Recommendation thresholds.
The system must create a new template version.
Existing assessments must retain the version originally assigned to them.
For example:
Opportunity A:
	•	Assessment Template V1.
	•	Strategic value weight: 15%.
	•	Final score: 77.
Administrator publishes V2:
	•	Strategic value weight: 20%.
Opportunity A must still display its original V1 assessment and score.
New assessments can use V2.
Reassessment against a new template version must be an explicit operation with a preserved relationship to the original assessment.

11. Non-Functional Requirements
Category
Requirement
Performance
Standard screens should load within 3 seconds under normal internal usage
Scalability
Support multiple business units and future assessment templates
Availability
Target 99.5% availability, subject to hosting infrastructure
Security
Enforce RBAC and secure data handling
Maintainability
Modular backend and reusable frontend components
Auditability
Maintain historical records of business decisions
Usability
Minimal training required for common assessment workflows
Compatibility
Latest Chrome, Edge and Safari
Localization
English initially; architecture should support Arabic later
Backup
Automated database backup and tested restoration
Reporting
Generate consistent, printable PDF reports

12. Development Roadmap
Phase 1 – Foundation
Deliverables:
	•	Project structure.
	•	Frontend setup.
	•	Backend setup.
	•	Database setup.
	•	Authentication.
	•	User and role management.
	•	Main navigation.
	•	Base UI design system.
Phase 2 – Configuration Engine
Deliverables:
	•	Assessment template management.
	•	Criteria configuration.
	•	Subcriteria configuration.
	•	Weight configuration.
	•	Scoring scale configuration.
	•	Recommendation thresholds.
	•	Template versioning.
	•	Configuration validation.
Phase 3 – Opportunity Assessment
Deliverables:
	•	Opportunity management.
	•	Assessment creation.
	•	Assessment execution.
	•	Scoring engine.
	•	Automatic recommendation.
	•	Evidence and comments.
	•	Assessment result dashboard.
Phase 4 – Governance
Deliverables:
	•	Risk register.
	•	Action plan.
	•	Approval workflow.
	•	Management override.
	•	Audit trail.
	•	Decision history.
Phase 5 – Business Intelligence
Deliverables:
	•	Commercial feasibility.
	•	Partner management.
	•	Resource feasibility.
	•	Executive dashboard.
	•	Opportunity comparison.
	•	PDF reporting.
Phase 6 – Advanced Intelligence
Deliverables:
	•	AI Executive Advisor.
	•	RFP analysis.
	•	AI-assisted assessment.
	•	Scenario simulator.
	•	Historical decision analytics.
	•	Market intelligence.

13. MVP Acceptance Criteria
The MVP should not be considered complete until the following scenarios work.
Scenario 1 – Assessment Configuration
	•	Administrator creates an assessment template.
	•	Adds seven evaluation criteria.
	•	Configures weights.
	•	Defines subcriteria.
	•	Defines a five-level scoring scale.
	•	Configures recommendation thresholds.
	•	Publishes the template.
	•	System validates that criterion weights total 100%.
Scenario 2 – Opportunity Registration
	•	Business Development Manager creates an opportunity.
	•	Assigns an owner.
	•	Enters client and commercial details.
	•	Selects an assessment template.
	•	Creates an assessment instance.
Scenario 3 – Scoring
	•	Evaluator completes all mandatory criteria.
	•	Adds justifications.
	•	Uploads supporting evidence.
	•	System calculates weighted scores.
	•	System generates the correct recommendation.
Scenario 4 – Recommendation
	•	Opportunity scores 77.
	•	System recommends conditional proceeding.
	•	Identifies weak criteria.
	•	Displays outstanding gaps.
	•	Produces recommended actions.
Scenario 5 – Executive Decision
	•	Executive reviews the assessment.
	•	Executive approves, rejects or requests reassessment.
	•	Executive can override the recommendation with mandatory justification.
	•	System records the decision and audit history.
Scenario 6 – Historical Integrity
	•	Administrator modifies assessment weights.
	•	Publishes a new template version.
	•	Existing assessments retain their original scoring methodology.
	•	New assessments use the new version.
Scenario 7 – Reporting
	•	User generates an assessment report.
	•	PDF includes all criteria, scores, recommendations, risks and management decisions.
	•	Report is printable and suitable for executive circulation.

14. Technical Development Standards for Cursor
The following standards should be followed during implementation.
14.1 Project Structure
Recommended repository structure:
diyar-compass/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   │   ├── dashboard/
│   │   ├── opportunities/
│   │   ├── assessments/
│   │   ├── configuration/
│   │   ├── partners/
│   │   ├── commercial/
│   │   ├── risks/
│   │   ├── approvals/
│   │   └── reports/
│   ├── hooks/
│   ├── lib/
│   ├── services/
│   ├── types/
│   └── styles/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── workflows/
│   │   ├── utils/
│   │   └── main.py
│   ├── migrations/
│   └── tests/
│
├── infrastructure/
│   ├── docker/
│   └── deployment/
│
├── docs/
│   ├── functional-specification.md
│   ├── technical-specification.md
│   ├── database-design.md
│   └── api-specification.md
│
├── docker-compose.yml
└── README.md
14.2 Coding Standards
	•	Use TypeScript for frontend development.
	•	Use Python type hints.
	•	Use Pydantic schemas for backend validation.
	•	Keep business logic outside API route handlers.
	•	Use reusable UI components.
	•	Use SQLAlchemy models and Alembic migrations.
	•	Maintain unit tests for scoring calculations.
	•	Maintain integration tests for workflows.
	•	Avoid hardcoded assessment criteria.
	•	Avoid hardcoded weights and thresholds.
	•	Never calculate authoritative scores only in the frontend.
	•	Validate permissions on the backend.
	•	Document API endpoints.
	•	Use environment variables for secrets and configuration.
14.3 Required Testing
At minimum:
	•	Scoring engine unit tests.
	•	Weight validation tests.
	•	Recommendation boundary tests.
	•	Template versioning tests.
	•	Role and permission tests.
	•	Opportunity workflow tests.
	•	Approval workflow tests.
	•	Financial calculation tests.
	•	API integration tests.

15. Cursor AI Development Instructions
Use the following instructions as the baseline development rules.
Cursor must follow these principles:
	•	Read the project specification before implementing each module.
	•	Do not attempt to build the entire application in one generation.
	•	Implement modules incrementally.
	•	Maintain a clean separation between frontend, backend and database.
	•	Never hardcode evaluation criteria, weights, scoring values or recommendation thresholds.
	•	Implement scoring calculations in the backend.
	•	Preserve assessment template versions.
	•	Use migrations for database schema changes.
	•	Write tests for business-critical logic.
	•	Maintain a consistent UI design system.
	•	Do not introduce unnecessary libraries or architectural complexity.
	•	Update technical documentation as the implementation evolves.
	•	Do not use mock data in production workflows.
	•	Clearly identify any functionality that is not yet implemented.
	•	Never claim a feature is complete without testing it.

16. Definition of Done
The first production-ready release of DIYAR COMPASS must allow Diyar to:
	•	Register and manage business opportunities.
	•	Configure assessment methodologies independently.
	•	Define evaluation criteria and weights.
	•	Configure scoring values.
	•	Configure recommendation thresholds.
	•	Evaluate opportunities.
	•	Calculate weighted scores automatically.
	•	Identify risks and delivery gaps.
	•	Generate executive recommendations.
	•	Route assessments for management approval.
	•	Record management decisions.
	•	Generate executive assessment reports.
	•	Maintain a complete historical and auditable record.
Final Product Vision
DIYAR COMPASS should become Diyar's central internal platform for strategic opportunity qualification, commercial evaluation and executive decision governance.
It should provide management with a consistent answer to one fundamental question:
"Is this the right opportunity for Diyar, and are we in the right position to pursue it successfully?"

