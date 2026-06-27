from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_api_key
from app.db.database import get_db
from app.db.models import Call, Load, NegotiationEvent
from app.schemas.negotiate import NegotiateRequest, NegotiateResponse
from app.services.negotiation import negotiate

router = APIRouter(tags=["negotiate"])


@router.post("/negotiate", response_model=NegotiateResponse)
async def negotiate_endpoint(
    body: NegotiateRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> NegotiateResponse:
    # Server derives round from event count — agent never supplies this.
    round_num: int = (
        await db.execute(
            select(func.count()).where(NegotiationEvent.run_id == body.run_id)
        )
    ).scalar_one() + 1

    load = (
        await db.execute(select(Load).where(Load.load_id == body.load_id))
    ).scalar_one_or_none()
    if load is None:
        raise HTTPException(status_code=404, detail=f"Load {body.load_id!r} not found")

    result = negotiate(
        carrier_offer=body.carrier_offer,
        loadboard_rate=load.loadboard_rate,
        pickup_date=load.pickup_datetime.date(),
        round_num=round_num,
    )

    now = datetime.utcnow()

    # Each invocation writes exactly one event row, advancing the round counter.
    db.add(NegotiationEvent(
        run_id=body.run_id,
        round=round_num,
        load_id=body.load_id,
        carrier_offer=body.carrier_offer,
        agent_price=result.agent_price,
        decision=result.decision,
        created_at=now,
    ))

    # On accept: minimal upsert of calls.final_rate only.
    # Does NOT touch outcome, outcome_source, sentiment, rounds, or any other column.
    # Creates the row if absent — /negotiate often runs before the post-call webhook.
    if result.decision == "accept":
        call = (
            await db.execute(select(Call).where(Call.run_id == body.run_id))
        ).scalar_one_or_none()

        if call is None:
            db.add(Call(
                run_id=body.run_id,
                load_id=body.load_id,
                final_rate=result.agent_price,
                created_at=now,
                updated_at=now,
            ))
        else:
            call.final_rate = result.agent_price
            if call.load_id is None:
                call.load_id = body.load_id
            call.updated_at = now

    await db.commit()

    return NegotiateResponse(
        run_id=body.run_id,
        round=round_num,
        decision=result.decision,
        agent_price=result.agent_price,
        ceiling=result.ceiling,
        negotiation_status=result.negotiation_status,
    )
