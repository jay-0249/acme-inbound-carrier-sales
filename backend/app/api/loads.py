from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_read_access
from app.db.database import get_db
from app.db.models import Load
from app.schemas.load import LoadResponse

router = APIRouter(prefix="/loads", tags=["loads"])


@router.get("", response_model=list[LoadResponse])
async def list_loads(
    equipment_type: Optional[str] = Query(None, description="Exact match on equipment type"),
    origin: Optional[str] = Query(None, description="Partial match on origin city/state"),
    destination: Optional[str] = Query(None, description="Partial match on destination city/state"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_read_access),
) -> list[Load]:
    stmt = select(Load)
    if equipment_type:
        stmt = stmt.where(Load.equipment_type == equipment_type)
    if origin:
        stmt = stmt.where(Load.origin.ilike(f"%{origin}%"))
    if destination:
        stmt = stmt.where(Load.destination.ilike(f"%{destination}%"))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{load_id}", response_model=LoadResponse)
async def get_load(
    load_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_read_access),
) -> Load:
    result = await db.execute(select(Load).where(Load.load_id == load_id))
    load = result.scalar_one_or_none()
    if load is None:
        raise HTTPException(status_code=404, detail=f"Load {load_id!r} not found")
    return load
