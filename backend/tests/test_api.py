import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("TESTING", "true")
os.environ.setdefault("SEED_SAMPLE_DATA", "false")
os.environ.setdefault("SECRET_KEY", "test-secret")

from app.core.config import get_settings
from app.main import app
from app.services.seed import DEMO_PASSWORD


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("SEED_SAMPLE_DATA", "false")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "storage"))
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def login(client, email, password=DEMO_PASSWORD):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_viewer_cannot_create_an_opportunity_and_manager_can(client):
    lookups = client.get("/api/v1/lookups", headers=login(client, "bd@diyar.local")).json()
    payload = {
        "name": "National EHR Programme",
        "client_name": "Ministry of Health",
        "country_id": lookups["countries"][0]["id"],
        "sector_id": lookups["sectors"][0]["id"],
        "description": "Replace the national electronic health record and integration layer.",
        "service_line_ids": [lookups["service_lines"][0]["id"]],
        "opportunity_source": "Government Tender",
        "estimated_value": 4800000,
        "currency_code": "AED",
        "owner_id": next(user["id"] for user in lookups["users"] if user["full_name"] == "Business Development Manager"),
        "partner_required": True,
    }
    denied = client.post("/api/v1/opportunities", headers=login(client, "viewer@diyar.local"), json=payload)
    assert denied.status_code == 403
    created = client.post("/api/v1/opportunities", headers=login(client, "bd@diyar.local"), json=payload)
    assert created.status_code == 200, created.text
    assert created.json()["reference_number"].startswith("OPP-")
    assert created.json()["status"] == "identified"


def test_score_77_recommends_closing_gaps_and_versions_stay_immutable(client):
    bd = login(client, "bd@diyar.local")
    admin = login(client, "admin@diyar.local")
    lookups = client.get("/api/v1/lookups", headers=bd).json()
    templates = client.get("/api/v1/assessment-templates", headers=bd).json()
    template_id = templates[0]["id"]
    opportunity = client.post(
        "/api/v1/opportunities",
        headers=bd,
        json={
            "name": "Regional HIS Modernisation",
            "client_name": "Health Authority",
            "country_id": lookups["countries"][0]["id"],
            "sector_id": lookups["sectors"][0]["id"],
            "description": "Modernise the regional hospital information system.",
            "service_line_ids": [lookups["service_lines"][0]["id"]],
            "opportunity_source": "Government Tender",
            "currency_code": "AED",
            "owner_id": next(user["id"] for user in lookups["users"] if user["full_name"] == "Business Development Manager"),
        },
    ).json()
    assessment = client.post("/api/v1/assessments", headers=bd, json={"opportunity_id": opportunity["id"], "template_id": template_id})
    assert assessment.status_code == 200, assessment.text
    body = assessment.json()
    version_id = body["template"]["version_id"]
    pattern = {
        "Strategic Business Value": 5,
        "Client Opportunity & Probability of Winning": 4,
        "Technical Delivery Capability": 3,
        "Partner Credibility & Commitment": 4,
        "Commercial Attractiveness": 4,
        "Resource Availability & Delivery Feasibility": 3,
        "Risk Management": 4,
    }
    subs = []
    responses = []
    for criterion in body["criteria"]:
        for sub in criterion["subcriteria"]:
            subs.append({"subcriterion_id": sub["id"], "selected_score": pattern[criterion["name"]], "comments": ""})
    for question in body["questions"]:
        if question["is_mandatory"]:
            responses.append({"question_id": question["id"], "response_text": "The rationale and delivery assumptions are documented."})
    saved = client.put(f"/api/v1/assessments/{body['id']}", headers=bd, json={"subcriterion_scores": subs, "responses": responses})
    assert saved.status_code == 200, saved.text
    blocked = client.post(f"/api/v1/assessments/{body['id']}/submit", headers=bd)
    assert blocked.status_code == 200, blocked.text
    result = blocked.json()
    assert result["calculated_score"] == 77
    assert result["recommendation_name"] == "Proceed subject to closing identified gaps"
    assert {gap["criterion_name"] for gap in result["gaps"]} == {
        "Technical Delivery Capability",
        "Resource Availability & Delivery Feasibility",
    }
    assert any(action["title"].startswith("Close gap:") for action in result["actions"])

    client.post(
        f"/api/v1/opportunities/{opportunity['id']}/commercial",
        headers=bd,
        json={"contract_value": 100, "currency_code": "AED", "internal_cost": 180, "probability_of_winning": 50},
    )
    recalculated = client.post(f"/api/v1/assessments/{body['id']}/recalculate", headers=bd).json()
    assert recalculated["calculated_score"] == 77
    assert any(flag["code"] == "negative_margin" for flag in recalculated["red_flags"])

    functional = login(client, "functional@diyar.local")
    commercial = login(client, "commercial@diyar.local")
    executive = login(client, "executive@diyar.local")
    assert client.post(
        f"/api/v1/assessments/{body['id']}/reviews",
        headers=functional,
        json={"stage": "functional_review", "decision": "confirmed", "comments": "Delivery feasibility is acceptable with the recorded gaps."},
    ).status_code == 200
    assert client.post(
        f"/api/v1/assessments/{body['id']}/reviews",
        headers=commercial,
        json={"stage": "commercial_review", "decision": "confirmed", "comments": "Commercial assumptions are visible and internally consistent."},
    ).status_code == 200
    override_denied = client.post(
        f"/api/v1/assessments/{body['id']}/approve",
        headers=executive,
        json={
            "decision": "approved",
            "comments": "Proceed despite the conditional recommendation.",
            "override_recommendation": "Proceed with the opportunity",
            "exception_justification": "The margin exception is accepted for this strategic account.",
        },
    )
    assert override_denied.status_code == 400
    approved = client.post(
        f"/api/v1/assessments/{body['id']}/approve",
        headers=executive,
        json={
            "decision": "approved",
            "comments": "Proceed despite the conditional recommendation.",
            "override_recommendation": "Proceed with the opportunity",
            "override_reason": "The client relationship justifies proceeding while the margin is repaired.",
            "exception_justification": "The negative margin is a planning estimate and is accepted for this pursuit.",
        },
    )
    assert approved.status_code == 200, approved.text
    detail = client.get(f"/api/v1/opportunities/{opportunity['id']}", headers=executive).json()
    assert detail["status"] == "approved"
    assert detail["decisions"][0]["is_override"] is True
    assert detail["decisions"][0]["calculated_recommendation"] == "Proceed subject to closing identified gaps"

    versioned = client.post(f"/api/v1/assessment-templates/{template_id}/versions", headers=admin)
    assert versioned.status_code == 200, versioned.text
    draft = versioned.json()["draft"]
    criteria = draft["criteria"]
    criteria[0]["weight"] = 20
    criteria[1]["weight"] = 5
    changed = client.put(
        f"/api/v1/assessment-templates/{template_id}",
        headers=admin,
        json={
            "criteria": criteria,
            "scale": draft["scale"],
            "recommendation_rules": draft["recommendation_rules"],
            "questions": draft["questions"],
            "gap_normalized_threshold": draft["gap_normalized_threshold"],
        },
    )
    assert changed.status_code == 200, changed.text
    published = client.post(f"/api/v1/assessment-templates/{template_id}/publish", headers=admin)
    assert published.status_code == 200, published.text
    preserved = client.get(f"/api/v1/assessments/{body['id']}", headers=bd).json()
    assert preserved["template"]["version_id"] == version_id
    assert preserved["calculated_score"] == 77
    fresh = client.post("/api/v1/assessments", headers=bd, json={"opportunity_id": opportunity["id"], "template_id": template_id}).json()
    assert fresh["template"]["version_id"] != version_id
    assert fresh["template"]["version_number"] == 2


def test_publish_rejects_weights_that_do_not_total_100(client):
    admin = login(client, "admin@diyar.local")
    created = client.post("/api/v1/assessment-templates", headers=admin, json={"name": "Trial template", "description": "Weight check"})
    assert created.status_code == 200, created.text
    template_id = created.json()["id"]
    draft = created.json()["draft"]
    refused = client.post(f"/api/v1/assessment-templates/{template_id}/publish", headers=admin)
    assert refused.status_code == 400
    draft["criteria"] = [
        {"name": "Only criterion", "weight": 90, "subcriteria": []},
    ]
    client.put(f"/api/v1/assessment-templates/{template_id}", headers=admin, json={"criteria": draft["criteria"]})
    refused = client.post(f"/api/v1/assessment-templates/{template_id}/publish", headers=admin)
    assert refused.status_code == 400
    draft["criteria"][0]["weight"] = 100
    client.put(f"/api/v1/assessment-templates/{template_id}", headers=admin, json={"criteria": draft["criteria"]})
    assert client.post(f"/api/v1/assessment-templates/{template_id}/publish", headers=admin).status_code == 200


def test_evaluator_can_score_only_assigned_criteria(client):
    bd = login(client, "bd@diyar.local")
    evaluator = login(client, "evaluator@diyar.local")
    lookups = client.get("/api/v1/lookups", headers=bd).json()
    template_id = client.get("/api/v1/assessment-templates", headers=bd).json()[0]["id"]
    opportunity = client.post(
        "/api/v1/opportunities",
        headers=bd,
        json={
            "name": "Assigned scoring",
            "client_name": "Clinic Group",
            "country_id": lookups["countries"][0]["id"],
            "sector_id": lookups["sectors"][0]["id"],
            "description": "Check that evaluators stay inside their assigned section.",
            "service_line_ids": [lookups["service_lines"][0]["id"]],
            "opportunity_source": "Referral",
            "currency_code": "AED",
            "owner_id": next(user["id"] for user in lookups["users"] if user["full_name"] == "Business Development Manager"),
        },
    ).json()
    assessment = client.post("/api/v1/assessments", headers=bd, json={"opportunity_id": opportunity["id"], "template_id": template_id}).json()
    evaluator_id = next(user["id"] for user in lookups["users"] if user["full_name"] == "Assessment Evaluator")
    first = assessment["criteria"][0]
    second = assessment["criteria"][1]
    assigned = client.put(
        f"/api/v1/assessments/{assessment['id']}",
        headers=bd,
        json={"assignments": [{"user_id": evaluator_id, "criterion_id": first["id"]}]},
    )
    assert assigned.status_code == 200, assigned.text
    denied = client.put(
        f"/api/v1/assessments/{assessment['id']}",
        headers=evaluator,
        json={"subcriterion_scores": [{"subcriterion_id": second["subcriteria"][0]["id"], "selected_score": 4, "comments": ""}]},
    )
    assert denied.status_code == 403
    allowed = client.put(
        f"/api/v1/assessments/{assessment['id']}",
        headers=evaluator,
        json={"subcriterion_scores": [{"subcriterion_id": first["subcriteria"][0]["id"], "selected_score": 4, "comments": ""}]},
    )
    assert allowed.status_code == 200, allowed.text
