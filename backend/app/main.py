from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router
from app.core.config import get_settings
from app.core.database import Base, make_engine, make_session_factory
from app.services.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    app.state.session_factory = factory
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    db = factory()
    try:
        seed_database(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    yield
    engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="DIYAR COMPASS", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api/v1")

    @app.get("/")
    def root():
        return {"product": "DIYAR COMPASS", "tagline": "Navigate Opportunities. Make Informed Decisions.", "docs": "/docs"}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
