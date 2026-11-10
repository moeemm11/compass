import uuid
from collections import defaultdict
from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.tables import Assessment, CommercialAssessment, Opportunity, User
from app.services.access import fail, has_permission
from app.services.assessments import can_view_opportunity, get_assessment, present_assessment
from app.services.portfolio import list_opportunities, present_commercial, present_opportunity, present_risk
from app.services.records import status_label
from app.services.workflow import pending_items


def dashboard(db: Session, user: User, filters: dict) -> dict:
    if not has_permission(user, "dashboard.view", db):
        fail(403, "You do not have permission to view the dashboard")
    items = _all_items(db, user, filters)
    ids = [uuid.UUID(item["id"]) for item in items]
    commercials = {}
    if ids:
        for row in db.scalars(select(CommercialAssessment).where(CommercialAssessment.opportunity_id.in_(ids))).all():
            commercials[row.opportunity_id] = row
    assessments = []
    if ids:
        assessments = db.scalars(select(Assessment).where(Assessment.opportunity_id.in_(ids)).order_by(Assessment.created_at.desc())).all()
    latest = {}
    for assessment in assessments:
        latest.setdefault(assessment.opportunity_id, assessment)

    def count_status(status):
        return sum(1 for item in items if item["status"] == status)

    pipeline = sum(item["estimated_value"] or 0 for item in items)
    risk_adjusted = sum(float(commercials[item_id].expected_revenue or 0) for item_id in commercials)
    scored = [assessment for assessment in latest.values() if assessment.scores_complete and assessment.calculated_score is not None]
    average = round(sum(float(item.calculated_score) for item in scored) / len(scored), 2) if scored else None

    def grouped(key):
        counts = defaultdict(int)
        for item in items:
            counts[item.get(key) or "Unspecified"] += 1
        return [{"label": str(label), "count": count} for label, count in sorted(counts.items(), key=lambda pair: (-pair[1], str(pair[0])))]

    by_country = defaultdict(int)
    by_owner = defaultdict(int)
    by_service = defaultdict(int)
    pipeline_by_status = defaultdict(float)
    for item in items:
        by_country[item["country"]["name"]] += 1
        by_owner[item["owner"]["full_name"]] += 1
        pipeline_by_status[item["status_label"]] += item["estimated_value"] or 0
        for line in item["service_lines"]:
            by_service[line["name"]] += 1

    months = defaultdict(list)
    for assessment in assessments:
        if assessment.submitted_at and assessment.calculated_score is not None:
            months[assessment.submitted_at.strftime("%Y-%m")].append(float(assessment.calculated_score))

    opportunities = {row.id: row for row in db.scalars(select(Opportunity).where(Opportunity.id.in_(ids))).all()} if ids else {}
    upcoming = []
    from app.models.tables import ActionItem

    if ids:
        actions = db.scalars(
            select(ActionItem)
            .where(ActionItem.opportunity_id.in_(ids), ActionItem.status.notin_(["completed", "cancelled"]))
            .order_by(ActionItem.due_date)
        ).all()
        today = date.today()
        for action in actions:
            if action.due_date and action.due_date >= today:
                opportunity = opportunities.get(action.opportunity_id)
                upcoming.append(
                    {
                        "id": str(action.id),
                        "title": action.title,
                        "due_date": action.due_date.isoformat(),
                        "opportunity_name": opportunity.name if opportunity else "",
                        "priority": action.priority,
                    }
                )
            if len(upcoming) == 6:
                break

    recent_decisions = []
    from app.models.tables import ManagementDecision

    if ids:
        decisions = db.scalars(
            select(ManagementDecision).where(ManagementDecision.opportunity_id.in_(ids)).order_by(ManagementDecision.decision_date.desc()).limit(6)
        ).all()
        for decision in decisions:
            opportunity = opportunities.get(decision.opportunity_id)
            recent_decisions.append(
                {
                    "opportunity_name": opportunity.name if opportunity else "",
                    "decision": decision.final_decision,
                    "recommendation": decision.calculated_recommendation,
                    "is_override": decision.is_override,
                    "decision_date": decision.decision_date.isoformat(),
                }
            )

    return {
        "kpis": {
            "total": len(items),
            "under_assessment": count_status("under_assessment") + count_status("under_qualification"),
            "awaiting_approval": count_status("awaiting_executive_decision"),
            "approved": count_status("approved"),
            "conditionally_approved": count_status("conditionally_approved"),
            "rejected": count_status("rejected"),
            "pipeline_value": round(pipeline, 2),
            "risk_adjusted_pipeline": round(risk_adjusted, 2),
            "average_score": average,
        },
        "by_status": [{"label": status_label(item["status"]), "count": count_status(item["status"])} for item in _unique_status(items)],
        "by_recommendation": grouped("recommendation"),
        "by_country": [{"label": label, "count": count} for label, count in sorted(by_country.items())],
        "by_service_line": [{"label": label, "count": count} for label, count in sorted(by_service.items())],
        "pipeline_by_status": [{"label": label, "value": round(value, 2)} for label, value in pipeline_by_status.items()],
        "scores_over_time": [
            {"label": label, "score": round(sum(values) / len(values), 2)} for label, values in sorted(months.items())
        ],
        "by_owner": [{"label": label, "count": count} for label, count in sorted(by_owner.items())],
        "win_loss": [
            {"label": "Won", "count": count_status("won")},
            {"label": "Lost", "count": count_status("lost")},
        ],
        "recent_opportunities": items[:5],
        "recent_submissions": [
            {
                "assessment_id": str(assessment.id),
                "assessment_number": assessment.assessment_number,
                "opportunity_name": opportunities.get(assessment.opportunity_id).name if opportunities.get(assessment.opportunity_id) else "",
                "submitted_at": assessment.submitted_at.isoformat() if assessment.submitted_at else None,
                "score": round(float(assessment.calculated_score), 2) if assessment.calculated_score is not None else None,
            }
            for assessment in sorted([item for item in assessments if item.submitted_at], key=lambda item: item.submitted_at, reverse=True)[:5]
        ],
        "pending_approvals": pending_items(db, user)[:6],
        "recent_decisions": recent_decisions,
        "upcoming_actions": upcoming,
        "notes": {
            "risk_adjusted_pipeline": "Sum of expected revenue (contract value × probability of winning) where a commercial assessment exists. Opportunities without a commercial assessment are excluded rather than treated as certain.",
        },
    }


def portfolio_report(db: Session, user: User, filters: dict) -> dict:
    if not has_permission(user, "reports.export", db) and not has_permission(user, "dashboard.view", db):
        fail(403, "You do not have permission to view reports")
    data = dashboard(db, user, filters)
    items = _all_items(db, user, filters)
    return {
        "summary": data["kpis"],
        "by_recommendation": data["by_recommendation"],
        "by_country": data["by_country"],
        "by_service_line": data["by_service_line"],
        "opportunities": items,
    }


def assessment_report(db: Session, user: User, assessment_id) -> dict:
    assessment = get_assessment(db, assessment_id)
    report = present_assessment(db, user, assessment)
    opportunity = db.get(Opportunity, assessment.opportunity_id)
    opportunity = db.scalar(
        select(Opportunity)
        .where(Opportunity.id == opportunity.id)
        .options(
            selectinload(Opportunity.country),
            selectinload(Opportunity.sector),
            selectinload(Opportunity.business_unit),
            selectinload(Opportunity.owner),
            selectinload(Opportunity.service_lines),
        )
    )
    detail = present_opportunity(db, opportunity, detailed=True)
    commercial = detail["commercial"]
    return {
        "generated_for": report["assessment_number"],
        "opportunity": detail,
        "assessment": report,
        "commercial": commercial,
        "risks": detail["risks"],
        "partners": detail["partners"],
        "resources": detail["resources"],
        "resource_summary": detail["resource_summary"],
        "actions": detail["actions"],
        "decisions": detail["decisions"],
        "approvals": detail["approvals"],
    }


def compare_assessments(db: Session, user: User, assessment_ids: list) -> dict:
    if len(assessment_ids) < 2:
        fail(400, "Select at least two assessments to compare")
    reports = []
    for assessment_id in assessment_ids:
        assessment = get_assessment(db, assessment_id)
        reports.append(present_assessment(db, user, assessment))
    versions = {item["template"]["version_id"] for item in reports}
    if len(versions) != 1:
        fail(400, "Comparison is only available for assessments that use the same template version")
    criteria_names = [criterion["name"] for criterion in reports[0]["criteria"]]
    rows = []
    for name in criteria_names:
        cells = []
        for report in reports:
            match = next(criterion for criterion in report["criteria"] if criterion["name"] == name)
            cells.append({"score": match["selected_score"], "weighted_score": match["weighted_score"]})
        rows.append({"criterion": name, "weight": next(c["weight"] for c in reports[0]["criteria"] if c["name"] == name), "scores": cells})
    return {
        "template": reports[0]["template"],
        "columns": [
            {"assessment_id": item["id"], "label": item["opportunity_name"], "score": item["calculated_score"], "recommendation": item["recommendation_name"]}
            for item in reports
        ],
        "rows": rows,
    }


def render_pdf(report: dict) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleNavy", parent=styles["Title"], textColor=colors.HexColor("#0B1F3A"), fontSize=18, leading=22)
    heading = ParagraphStyle("HeadingNavy", parent=styles["Heading2"], textColor=colors.HexColor("#0B1F3A"), fontSize=12, spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9, leading=12, textColor=colors.HexColor("#122033"))
    small = ParagraphStyle("Small", parent=body, fontSize=8, textColor=colors.HexColor("#5C6B7A"))
    opportunity = report["opportunity"]
    assessment = report["assessment"]
    story = [
        Paragraph("DIYAR COMPASS", title),
        Paragraph("Navigate Opportunities. Make Informed Decisions.", small),
        Spacer(1, 6),
        Paragraph(f"Executive Assessment Report · {assessment['assessment_number']}", heading),
        Paragraph(f"{opportunity['reference_number']} — {opportunity['name']}", body),
        Paragraph(f"Client: {opportunity['client_name']} · {opportunity['country']['name']} · {opportunity['status_label']}", body),
        Paragraph(f"Template {assessment['template']['name']} version {assessment['template']['version_number']}", small),
        Spacer(1, 8),
        Paragraph("Opportunity overview", heading),
        Paragraph(opportunity["description"], body),
        Paragraph(
            f"Source: {opportunity['opportunity_source']}. Service lines: {', '.join(line['name'] for line in opportunity['service_lines']) or 'None'}. "
            f"Estimated value: {opportunity['estimated_value'] or '—'} {opportunity['currency_code']}. Owner: {opportunity['owner']['full_name']}.",
            body,
        ),
        Paragraph("Assessment result", heading),
        Paragraph(
            f"Overall score {assessment['calculated_score'] if assessment['calculated_score'] is not None else '—'} / 100. "
            f"Recommendation: {assessment['recommendation_name'] or 'Not available until the assessment is complete.'}",
            body,
        ),
        Paragraph(assessment.get("recommendation_description") or "", body),
        Paragraph(f"Recommended management action: {assessment.get('recommendation_action') or '—'}", body),
    ]
    if assessment.get("red_flags"):
        story.append(Paragraph("Critical red flags — these do not change the score", heading))
        for flag in assessment["red_flags"]:
            story.append(Paragraph(f"• {flag['name']}: {flag['detail']}", body))
    story.append(Paragraph("Criteria and scores", heading))
    table_data = [["Criterion", "Weight", "Score", "Weighted"]]
    for criterion in assessment["criteria"]:
        table_data.append(
            [
                criterion["name"],
                f"{criterion['weight']}%",
                "—" if criterion["selected_score"] is None else str(criterion["selected_score"]),
                "—" if criterion["weighted_score"] is None else str(criterion["weighted_score"]),
            ]
        )
    table_data.append(["Overall", "100%", "", str(assessment["calculated_score"] if assessment["calculated_score"] is not None else "—")])
    table = Table(table_data, colWidths=[85 * mm, 25 * mm, 30 * mm, 30 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E6F2F1")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5DDE5")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(Paragraph("Strengths", heading))
    story.append(Paragraph(", ".join(item["criterion_name"] for item in assessment["strengths"]) or "None recorded.", body))
    story.append(Paragraph("Gaps", heading))
    if assessment["gaps"]:
        for gap in assessment["gaps"]:
            story.append(Paragraph(f"• {gap['summary']} {gap['suggestion']}", body))
    else:
        story.append(Paragraph("No criterion is at or below the configured gap threshold.", body))
    story.append(Paragraph("Risks", heading))
    if report["risks"]:
        for risk in report["risks"]:
            story.append(
                Paragraph(
                    f"• {risk['reference_number']} {risk['title']} ({risk['category']}) — inherent {risk['inherent_score']}, residual {risk['residual_score'] or '—'}, {risk['status']}. {risk['mitigation_plan']}",
                    body,
                )
            )
    else:
        story.append(Paragraph("No risks recorded.", body))
    story.append(Paragraph("Commercial feasibility", heading))
    commercial = report["commercial"]
    if commercial:
        story.append(Paragraph(commercial["figures_label"], small))
        story.append(
            Paragraph(
                f"Contract {commercial['contract_value']} {commercial['currency_code']}. Cost {commercial['total_cost']}. "
                f"Gross profit {commercial['gross_profit']} ({commercial['gross_margin']}%). Expected revenue {commercial['expected_revenue']}. "
                f"Expected contribution {commercial['expected_contribution']}. Partner cost share {commercial['partner_cost_percentage']}%. "
                f"Bid preparation {commercial['bid_cost']}. Probability of winning {commercial['probability_of_winning']}%.",
                body,
            )
        )
        if commercial["assumptions"]:
            story.append(Paragraph(f"Assumptions: {commercial['assumptions']}", body))
    else:
        story.append(Paragraph("No commercial assessment has been recorded.", body))
    story.append(Paragraph("Partners and resources", heading))
    if report["partners"]:
        story.append(Paragraph("; ".join(f"{item['name']} ({item['commitment_status']}, {item['role']})" for item in report["partners"]), body))
    else:
        story.append(Paragraph("No partners linked.", body))
    summary = report["resource_summary"]
    story.append(
        Paragraph(
            f"Delivery feasibility: {summary['delivery_feasibility']}. Demand {summary['total_demand']}. "
            f"Confirmed internal {summary['confirmed_internal']}. External dependency {summary['external_dependency']}. "
            f"Critical gaps {summary['critical_skill_gaps']}.",
            body,
        )
    )
    story.append(Paragraph("Required actions", heading))
    if report["actions"]:
        for action in report["actions"]:
            mandatory = " Mandatory before commitment." if action["is_mandatory_for_commitment"] else ""
            story.append(Paragraph(f"• {action['reference_number']} {action['title']} — {action['status']}, {action['priority']}.{mandatory}", body))
    else:
        story.append(Paragraph("No actions recorded.", body))
    story.append(Paragraph("Management decision and approval history", heading))
    if report["decisions"]:
        for decision in report["decisions"]:
            override = ""
            if decision["is_override"]:
                override = f" Override of {decision['calculated_recommendation']} to {decision['override_recommendation']}: {decision['override_reason']}."
            story.append(
                Paragraph(
                    f"• {decision['decision_date']}: {decision['final_decision']} by {decision['decision_maker']}. "
                    f"System recommendation was {decision['calculated_recommendation']} ({decision['calculated_score']}).{override} "
                    f"{decision['exception_justification']}",
                    body,
                )
            )
    else:
        story.append(Paragraph("No management decision has been recorded.", body))
    for approval in report["approvals"]:
        story.append(Paragraph(f"• {approval['decided_at']}: {approval['stage']} — {approval['decision']} by {approval['approver']}. {approval['comments']}", small))
    story.append(Spacer(1, 12))
    story.append(Paragraph("This report preserves the template version used for the assessment. Later changes to weights or thresholds do not alter this result.", small))
    document.build(story)
    return buffer.getvalue()


def _all_items(db: Session, user: User, filters: dict) -> list[dict]:
    collected = []
    page = 1
    total = None
    while total is None or len(collected) < total:
        result = list_opportunities(db, user, page=page, page_size=100, **filters)
        total = result["total"]
        collected.extend(result["items"])
        if not result["items"]:
            break
        page += 1
    return collected


def _unique_status(items: list[dict]) -> list[dict]:
    seen = []
    for item in items:
        if item["status"] not in {row["status"] for row in seen}:
            seen.append(item)
    return seen
