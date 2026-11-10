# DIYAR COMPASS

Executive decision intelligence for qualifying, scoring, and approving business opportunities.

The question the platform answers is: **is this the right opportunity for Diyar, and are we in the right position to pursue it?**

## Run it locally

The supported production database is PostgreSQL. For a local demonstration the API starts on SQLite, so no database server is required.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. API docs are at http://localhost:8000/docs.

Demonstration password for every seeded account: `Compass123!`

| Email | Role |
| --- | --- |
| admin@diyar.local | System Administrator |
| bd@diyar.local | Business Development Manager |
| evaluator@diyar.local | Assessment Evaluator |
| functional@diyar.local | Functional Reviewer |
| commercial@diyar.local | Commercial Reviewer |
| executive@diyar.local | Executive Approver |
| viewer@diyar.local | Executive Viewer |

Sample opportunities are created on the first launch and are named `Sample:`. Set `SEED_SAMPLE_DATA=false` before the first launch to start with an empty portfolio. Delete `backend/diyar_compass.db` to reseed.

## PostgreSQL

```bash
docker compose up --build
```

That starts PostgreSQL, the API, and the web app. Set a real `SECRET_KEY` before any shared deployment.

## What this release does

- Role-based sign-in, users, and permissions. Administrator approval rights are a separate setting.
- Configurable assessment templates: criteria, subcriteria, weights, scoring scale, questions, and recommendation bands.
- Published template versions are immutable. Existing assessments keep the version they were scored against.
- Weighted scoring and recommendations are calculated only on the server. Missing scores are not treated as zero and weights are not redistributed.
- A score of 77 on the default scale recommends proceeding subject to closing identified gaps.
- Risks, commercial feasibility, partners, resources, actions, reviews, executive override, and an audit log.
- Red flags escalate an opportunity and do not change the score.
- Executive PDF reports.

## Not in this release

- AI executive advisor, automated RFP analysis, and AI-assisted scoring.
- Scenario simulation and market-intelligence feeds.
- Partner-to-opportunity matching recommendations.
- Calendar-based resource capacity.
- Currency conversion. Amounts must use the opportunity currency.
- Conditional questions.
- Arabic interface. The structure is ready for a later locale; the product is English.

## Tests

```bash
cd backend && .venv/bin/pytest
```

The scoring, threshold, weight, financial, permission, and template-version tests cover the acceptance scenarios in the specification.
