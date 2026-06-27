from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_api_key
from app.db.database import get_db
from app.db.models import Call, Load, NegotiationEvent
from app.schemas.call import CallCreate, CallResponse

router = APIRouter(tags=["calls"])


@router.post("/calls", response_model=CallResponse, status_code=200)
async def upsert_call(
    body: CallCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> Call:
    now = datetime.utcnow()

    rounds_count: int = (
        await db.execute(
            select(func.count()).where(NegotiationEvent.run_id == body.run_id)
        )
    ).scalar_one()

    result = await db.execute(select(Call).where(Call.run_id == body.run_id))
    call = result.scalar_one_or_none()

    if call is None:
        # Determine outcome_source for a new row: default to "classified" when an
        # outcome is supplied but no explicit source is given.
        outcome_source = body.outcome_source
        if body.outcome is not None and outcome_source is None:
            outcome_source = "classified"

        call = Call(
            run_id=body.run_id,
            mc_number=body.mc_number,
            carrier_name=body.carrier_name,
            carrier_eligible=body.carrier_eligible,
            load_id=body.load_id,
            outcome=body.outcome,
            outcome_source=outcome_source,
            sentiment=body.sentiment,
            final_rate=body.final_rate,
            duration=body.duration,
            run_url=body.run_url,
            rounds=rounds_count or None,
            created_at=now,
            updated_at=now,
        )
        db.add(call)
    else:
        # Resolve-outcome protection: a "resolved" outcome_source on the existing row
        # cannot be overwritten by an incoming "classified" (or absent) source.
        incoming_outcome = body.outcome
        incoming_source = body.outcome_source
        if call.outcome_source == "resolved" and incoming_source != "resolved":
            incoming_outcome = None
            incoming_source = None

        if body.mc_number is not None:
            call.mc_number = body.mc_number
        if body.carrier_name is not None:
            call.carrier_name = body.carrier_name
        if body.carrier_eligible is not None:
            call.carrier_eligible = body.carrier_eligible
        if body.load_id is not None:
            call.load_id = body.load_id
        if incoming_outcome is not None:
            call.outcome = incoming_outcome
        if incoming_source is not None:
            call.outcome_source = incoming_source
        if body.sentiment is not None:
            call.sentiment = body.sentiment
        if body.final_rate is not None:
            call.final_rate = body.final_rate
        if body.duration is not None:
            call.duration = body.duration
        if body.run_url is not None:
            call.run_url = body.run_url

        call.rounds = rounds_count or call.rounds
        call.updated_at = now

    # Resolve final_rate for booked calls that bypassed /negotiate.
    # Resolution order: accept-event price (already set) > loadboard_rate for
    # booked > null. Never infer from the agent's last counter offer.
    if call.final_rate is None and call.outcome == "booked" and call.load_id is not None:
        load_res = await db.execute(select(Load).where(Load.load_id == call.load_id))
        booked_load = load_res.scalar_one_or_none()
        if booked_load is not None:
            call.final_rate = booked_load.loadboard_rate

    await db.commit()
    await db.refresh(call)
    return call
