from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import app.models
from app.api.auth import router as auth_router
from app.api.phase0 import router as phase0_router
from app.api.users import router as users_router
from app.core.config import get_settings
from app.core.database import Base, engine, ensure_sqlite_phase1_schema

settings = get_settings()
Base.metadata.create_all(bind=engine)
ensure_sqlite_phase1_schema()

app = FastAPI(title="Launch Circle API", version="0.1.0", debug=False)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        ) from exc
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(phase0_router)
app.include_router(users_router)
