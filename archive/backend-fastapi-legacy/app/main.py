from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    audit,
    exports,
    external_profiles,
    health,
    matching,
    memberships,
    persons,
    review_queue,
    sync,
    tiers,
)

app = FastAPI(
    title="Delphi Member OS API",
    version="1.0.0",
    description="Contact rectification and membership normalization platform for The Delphi Network.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(persons.router, prefix=API_PREFIX)
app.include_router(external_profiles.router, prefix=API_PREFIX)
app.include_router(tiers.router, prefix=API_PREFIX)
app.include_router(memberships.router, prefix=API_PREFIX)
app.include_router(matching.router, prefix=API_PREFIX)
app.include_router(review_queue.router, prefix=API_PREFIX)
app.include_router(sync.router, prefix=API_PREFIX)
app.include_router(exports.router, prefix=API_PREFIX)
app.include_router(audit.router, prefix=API_PREFIX)
