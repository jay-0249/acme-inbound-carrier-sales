import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.calls import router as calls_router
from app.api.carrier import router as carrier_router
from app.api.loads import router as loads_router
from app.db.database import Base, get_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("TESTING"):
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        from app.db.seed import seed_loads
        await seed_loads()
    yield


app = FastAPI(
    title="Inbound Carrier Sales API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(loads_router)
app.include_router(carrier_router)
app.include_router(calls_router)
