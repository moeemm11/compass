DIYAR COMPASS is a modular monolith.

- `frontend` is a Next.js application. It renders the workspace, validates forms locally, and never calculates the authoritative score.
- `backend` is a FastAPI application. Scoring, recommendations, permissions, workflow, and PDF generation live here.
- PostgreSQL is the production database. SQLAlchemy models use UUID keys and JSON that maps to JSONB on PostgreSQL. Local runs default to SQLite so the product can be opened without extra infrastructure.
- Files are stored on disk (or a mounted volume), not in the database.
- Published assessment template versions are immutable. Assessments store `template_version_id` and keep that methodology after a newer version is published.

See `docs/functional-specification.md` for the product baseline.
