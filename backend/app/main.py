import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.calls import router as calls_router
from app.api.carrier import router as carrier_router
from app.api.loads import router as loads_router
from app.api.metrics import router as metrics_router
from app.api.negotiate import router as negotiate_router
from app.db.database import Base, get_engine

# Resolve the built SPA directory (sibling to backend/)
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("TESTING"):
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        from app.db.seed import seed_calls, seed_loads
        await seed_loads()
        await seed_calls()
    yield


app = FastAPI(
    title="Inbound Carrier Sales API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(loads_router)
app.include_router(carrier_router)
app.include_router(calls_router)
app.include_router(negotiate_router)
app.include_router(metrics_router)

# Serve the built React SPA at "/" — must be mounted last so API routes
# take precedence. html=True enables SPA fallback (returns index.html for
# unknown paths, letting React Router handle client-side navigation).
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="spa")
