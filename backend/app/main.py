from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.security import get_current_user
from app.routers import (
    medicines, batches, sales, stock, expiry, predictions, alerts, auth,
    packs, dispense, writeoffs, touchstore, reorder, risk,
    cd_register, duty_register, cd_destruction, cd_anomalies,
    integration,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database on startup."""
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Pharmacy Stock Prediction System API — manages medicines, batches, "
        "sales, expiry tracking, and ML-powered demand forecasting."
    ),
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth router (public — no JWT required) ────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1")

# ── Protected routers (JWT required on every endpoint) ───────────────────────
_protected = {"dependencies": [__import__("fastapi").Depends(get_current_user)]}

app.include_router(medicines.router,   prefix="/api/v1", **_protected)
app.include_router(batches.router,     prefix="/api/v1", **_protected)
app.include_router(sales.router,       prefix="/api/v1", **_protected)
app.include_router(stock.router,       prefix="/api/v1", **_protected)
app.include_router(expiry.router,      prefix="/api/v1", **_protected)
app.include_router(predictions.router, prefix="/api/v1", **_protected)
app.include_router(alerts.router,      prefix="/api/v1", **_protected)
app.include_router(packs.router,       prefix="/api/v1", **_protected)
app.include_router(dispense.router,    prefix="/api/v1", **_protected)
app.include_router(writeoffs.router,   prefix="/api/v1", **_protected)
app.include_router(touchstore.router,  prefix="/api/v1", **_protected)
app.include_router(reorder.router,     prefix="/api/v1", **_protected)
app.include_router(risk.router,        prefix="/api/v1", **_protected)
app.include_router(cd_register.router,   prefix="/api/v1", **_protected)
app.include_router(duty_register.router, prefix="/api/v1", **_protected)
app.include_router(cd_destruction.router, prefix="/api/v1", **_protected)
app.include_router(cd_anomalies.router,  prefix="/api/v1", **_protected)
app.include_router(integration.router,   prefix="/api/v1", **_protected)


@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
