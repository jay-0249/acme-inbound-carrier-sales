from collections import Counter, defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_api_key
from app.db.database import get_db
from app.db.models import Call, Load, NegotiationEvent
from app.schemas.metrics import (
    CapacityMetrics,
    MarginMetrics,
    MetricsResponse,
    NegotiationMetrics,
    OutcomeCount,
    RecentCall,
    SentimentCounts,
    TopDeclineReason,
    UrgencyTierMetric,
    ValueModel,
)

router = APIRouter(tags=["metrics"])

_NON_AUTOMATED = {"transferred_to_human"}

_URGENCY_TIERS = [
    ("<=2 days (8%)", lambda d: d <= 2),
    ("3-5 days (6%)", lambda d: 3 <= d <= 5),
    (">5 days (4%)",  lambda d: d > 5),
]


def _is_after_hours(ts: datetime) -> bool:
    """Before 8am or after 6pm local (UTC proxy), or Saturday/Sunday."""
    if ts.weekday() >= 5:  # Saturday=5, Sunday=6
        return True
    return ts.hour < 8 or ts.hour >= 18


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> MetricsResponse:
    calls_result = await db.execute(select(Call))
    all_calls: list[Call] = list(calls_result.scalars().all())

    loads_result = await db.execute(select(Load))
    loads_by_id: dict[str, Load] = {lo.load_id: lo for lo in loads_result.scalars().all()}

    events_result = await db.execute(select(NegotiationEvent))
    all_events: list[NegotiationEvent] = list(events_result.scalars().all())

    total = len(all_calls)
    today = datetime.utcnow().date()

    # --- Capacity ---
    booked_calls = [c for c in all_calls if c.outcome == "booked"]
    non_automated = [c for c in all_calls if c.outcome in _NON_AUTOMATED]
    after_hours = [c for c in all_calls if _is_after_hours(c.created_at)]

    booking_rate = len(booked_calls) / total if total else 0.0
    automation_rate = (total - len(non_automated)) / total if total else 0.0

    total_duration = sum(c.duration or 0.0 for c in all_calls)
    rep_hours_freed = total_duration / 3600.0
    wage = 48.0
    agent_cost = 0.75
    value_captured = rep_hours_freed * wage - total * agent_cost

    # --- Margin (booked calls with a load and final_rate) ---
    booked_with_load = [
        c for c in booked_calls
        if c.load_id and c.final_rate is not None and c.load_id in loads_by_id
    ]

    pct_over_list = []
    dollars_over_list = []
    for c in booked_with_load:
        lb = loads_by_id[c.load_id].loadboard_rate
        pct_over_list.append((c.final_rate - lb) / lb)
        dollars_over_list.append(c.final_rate - lb)

    avg_pct_over = sum(pct_over_list) / len(pct_over_list) if pct_over_list else 0.0
    total_dollars_over = sum(dollars_over_list)

    tier_rows: list[UrgencyTierMetric] = []
    for label, predicate in _URGENCY_TIERS:
        tier_calls = [
            c for c in booked_with_load
            if predicate((loads_by_id[c.load_id].pickup_datetime.date() - today).days)
        ]
        if tier_calls:
            lbs = [loads_by_id[c.load_id].loadboard_rate for c in tier_calls]
            avg_t = sum(
                (c.final_rate - lb) / lb
                for c, lb in zip(tier_calls, lbs)
            ) / len(tier_calls)
        else:
            avg_t = 0.0
        tier_rows.append(UrgencyTierMetric(
            tier=label,
            avg_pct_over_loadboard=round(avg_t, 6),
            loads=len(tier_calls),
        ))

    # --- Outcomes ---
    outcome_counter: Counter = Counter(c.outcome or "unknown" for c in all_calls)
    sorted_outcomes = outcome_counter.most_common()
    outcomes_list = [
        OutcomeCount(
            outcome=out,
            count=cnt,
            pct=cnt / total if total else 0.0,
        )
        for out, cnt in sorted_outcomes
    ]

    non_booked = [(out, cnt) for out, cnt in sorted_outcomes if out != "booked"]
    if non_booked:
        top_decline_out, top_decline_cnt = non_booked[0]
    else:
        top_decline_out, top_decline_cnt = "none", 0

    # --- Sentiment ---
    sentiment_counter: Counter = Counter(c.sentiment or "neutral" for c in all_calls)

    # --- Negotiation ---
    # Booked calls that went through at least one negotiation round
    booked_run_ids = {c.run_id for c in booked_calls}
    events_by_run: dict[str, list[NegotiationEvent]] = defaultdict(list)
    for ev in all_events:
        events_by_run[ev.run_id].append(ev)

    negotiated_booked_rounds: list[int] = []
    settled_dist: dict[str, int] = {"round_1": 0, "round_2": 0, "round_3": 0, "walked": 0}

    for run_id, evs in events_by_run.items():
        n_rounds = len(evs)
        last_decision = evs[-1].decision if evs else None
        if run_id in booked_run_ids and last_decision == "accept":
            negotiated_booked_rounds.append(n_rounds)
            key = f"round_{n_rounds}" if n_rounds <= 3 else "round_3"
            settled_dist[key] = settled_dist.get(key, 0) + 1
        elif last_decision == "final":
            settled_dist["walked"] += 1

    avg_rounds_to_close = (
        sum(negotiated_booked_rounds) / len(negotiated_booked_rounds)
        if negotiated_booked_rounds else 0.0
    )

    # --- Recent calls (newest first, cap 25) ---
    sorted_calls = sorted(all_calls, key=lambda c: c.created_at, reverse=True)[:25]
    recent: list[RecentCall] = []
    for c in sorted_calls:
        lb = loads_by_id[c.load_id].loadboard_rate if c.load_id and c.load_id in loads_by_id else None
        if lb is not None and c.final_rate is not None:
            pct_over = (c.final_rate - lb) / lb
        else:
            pct_over = None
        recent.append(RecentCall(
            run_id=c.run_id,
            carrier_name=c.carrier_name,
            load_id=c.load_id,
            outcome=c.outcome,
            sentiment=c.sentiment,
            final_rate=c.final_rate,
            loadboard_rate=lb,
            pct_over_loadboard=round(pct_over, 6) if pct_over is not None else None,
            rounds=c.rounds,
            created_at=c.created_at.isoformat(),
            run_url=c.run_url,
        ))

    return MetricsResponse(
        capacity=CapacityMetrics(
            calls_handled=total,
            calls_after_hours=len(after_hours),
            calls_missed=0,
            booking_rate=round(booking_rate, 6),
            loads_booked=len(booked_calls),
            automation_rate=round(automation_rate, 6),
        ),
        value_model=ValueModel(
            rep_hours_freed=round(rep_hours_freed, 4),
            assumed_loaded_wage_per_hour=wage,
            assumed_agent_cost_per_call=agent_cost,
            value_captured_usd=round(value_captured, 2),
        ),
        margin=MarginMetrics(
            avg_pct_over_loadboard=round(avg_pct_over, 6),
            total_dollars_over_loadboard=round(total_dollars_over, 2),
            by_urgency_tier=tier_rows,
        ),
        outcomes=outcomes_list,
        top_decline_reason=TopDeclineReason(outcome=top_decline_out, count=top_decline_cnt),
        sentiment=SentimentCounts(
            positive=sentiment_counter.get("positive", 0),
            neutral=sentiment_counter.get("neutral", 0),
            negative=sentiment_counter.get("negative", 0),
        ),
        negotiation=NegotiationMetrics(
            avg_rounds_to_close=round(avg_rounds_to_close, 4),
            settled_distribution=settled_dist,
        ),
        recent_calls=recent,
    )
