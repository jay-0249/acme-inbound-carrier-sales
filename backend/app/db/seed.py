from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Call, Load, NegotiationEvent


def _dt(days: int, hour: int) -> datetime:
    """Naive datetime at `hour` on the date `days` from today. Evaluated at import time."""
    d = date.today() + timedelta(days=days)
    return datetime(d.year, d.month, d.day, hour)


# Pickup dates are relative to today so urgency tiers are always demoable:
#   days_to_pickup <= 2  -> 8% ceiling tier  (LD-001, LD-002, LD-010)
#   3 <= days <= 5       -> 6% ceiling tier  (LD-008, LD-003, LD-004)
#   days > 5             -> 4% ceiling tier  (LD-005, LD-006, LD-007, LD-009)
SEED_LOADS: list[dict] = [
    # --- URGENT (<=2 days, 8% ceiling) ---
    {
        "load_id": "LD-001",
        "origin": "Chicago, IL",
        "destination": "Detroit, MI",
        "pickup_datetime": _dt(0, 8),
        "delivery_datetime": _dt(0, 16),
        "equipment_type": "dry_van",
        "loadboard_rate": 1250.0,
        "notes": "Dock appointment required. Contact warehouse 30 min before arrival.",
        "weight": 38000,
        "commodity_type": "Electronics",
        "num_of_pieces": 24,
        "miles": 281,
        "dimensions": "48x96x96 in",
    },
    {
        "load_id": "LD-002",
        "origin": "Dallas, TX",
        "destination": "Atlanta, GA",
        "pickup_datetime": _dt(1, 6),
        "delivery_datetime": _dt(2, 10),
        "equipment_type": "reefer",
        "loadboard_rate": 2100.0,
        "notes": "Temp 34F. Fresh produce, time critical. Continuous temp log required.",
        "weight": 42000,
        "commodity_type": "Fresh Produce",
        "num_of_pieces": 860,
        "miles": 780,
        "dimensions": "48x96x96 in",
    },
    {
        "load_id": "LD-010",
        "origin": "Atlanta, GA",
        "destination": "Boston, MA",
        "pickup_datetime": _dt(2, 10),
        "delivery_datetime": _dt(3, 18),
        "equipment_type": "dry_van",
        "loadboard_rate": 2750.0,
        "notes": "Medical supplies. Handle with care. No stacking.",
        "weight": 36000,
        "commodity_type": "Medical Supplies",
        "num_of_pieces": 80,
        "miles": 1110,
        "dimensions": "48x96x96 in",
    },
    # --- MODERATE (3-5 days, 6% ceiling) ---
    {
        "load_id": "LD-008",
        "origin": "Kansas City, MO",
        "destination": "Denver, CO",
        "pickup_datetime": _dt(3, 8),
        "delivery_datetime": _dt(4, 8),
        "equipment_type": "reefer",
        "loadboard_rate": 2400.0,
        "notes": "HAZMAT Class 9. Temp 36-46F. Driver must have HAZMAT endorsement.",
        "weight": 30000,
        "commodity_type": "Pharmaceuticals",
        "num_of_pieces": 200,
        "miles": 600,
        "dimensions": "48x96x96 in",
    },
    {
        "load_id": "LD-003",
        "origin": "Houston, TX",
        "destination": "Charlotte, NC",
        "pickup_datetime": _dt(4, 7),
        "delivery_datetime": _dt(5, 15),
        "equipment_type": "flatbed",
        "loadboard_rate": 3200.0,
        "notes": "OVERSIZE. Width 14 ft. Pilot car required. Permit in progress.",
        "weight": 48000,
        "commodity_type": "Steel Beams",
        "num_of_pieces": 12,
        "miles": 1310,
        "dimensions": "48x14x8 ft",
    },
    {
        "load_id": "LD-004",
        "origin": "Los Angeles, CA",
        "destination": "Phoenix, AZ",
        "pickup_datetime": _dt(5, 9),
        "delivery_datetime": _dt(5, 18),
        "equipment_type": "dry_van",
        "loadboard_rate": 950.0,
        "notes": None,
        "weight": 35000,
        "commodity_type": "Apparel",
        "num_of_pieces": 120,
        "miles": 370,
        "dimensions": "48x96x96 in",
    },
    # --- LOW URGENCY (>5 days, 4% ceiling) ---
    {
        "load_id": "LD-005",
        "origin": "Memphis, TN",
        "destination": "Miami, FL",
        "pickup_datetime": _dt(7, 6),
        "delivery_datetime": _dt(8, 14),
        "equipment_type": "reefer",
        "loadboard_rate": 2800.0,
        "notes": "Temp -10F. Frozen food. Keep doors closed at all times.",
        "weight": 44000,
        "commodity_type": "Frozen Food",
        "num_of_pieces": 400,
        "miles": 1050,
        "dimensions": "48x96x96 in",
    },
    {
        "load_id": "LD-006",
        "origin": "Pittsburgh, PA",
        "destination": "Nashville, TN",
        "pickup_datetime": _dt(9, 8),
        "delivery_datetime": _dt(10, 12),
        "equipment_type": "flatbed",
        "loadboard_rate": 1800.0,
        "notes": "Tarps required. Secure construction equipment with chains.",
        "weight": 52000,
        "commodity_type": "Construction Equipment",
        "num_of_pieces": 4,
        "miles": 590,
        "dimensions": "48x10x9 ft",
    },
    {
        "load_id": "LD-007",
        "origin": "Seattle, WA",
        "destination": "Salt Lake City, UT",
        "pickup_datetime": _dt(11, 10),
        "delivery_datetime": _dt(12, 16),
        "equipment_type": "dry_van",
        "loadboard_rate": 1650.0,
        "notes": None,
        "weight": 40000,
        "commodity_type": "Consumer Goods",
        "num_of_pieces": 300,
        "miles": 840,
        "dimensions": "53x96x96 in",
    },
    {
        "load_id": "LD-009",
        "origin": "Cleveland, OH",
        "destination": "Indianapolis, IN",
        "pickup_datetime": _dt(14, 7),
        "delivery_datetime": _dt(14, 15),
        "equipment_type": "flatbed",
        "loadboard_rate": 2100.0,
        "notes": "Heavy industrial machinery. Crane offload required at destination.",
        "weight": 55000,
        "commodity_type": "Industrial Machinery",
        "num_of_pieces": 2,
        "miles": 300,
        "dimensions": "48x12x10 ft",
    },
]


async def seed_loads(session: AsyncSession | None = None) -> None:
    """Insert seed loads if the table is empty. Idempotent."""
    owns_session = session is None
    if owns_session:
        from app.db.database import _init_engine
        from sqlalchemy.ext.asyncio import async_sessionmaker
        _, maker = _init_engine()
        session = maker()

    try:
        result = await session.execute(select(Load).limit(1))
        if result.scalar_one_or_none() is not None:
            return
        for data in SEED_LOADS:
            session.add(Load(**data))
        await session.commit()
    finally:
        if owns_session:
            await session.close()


# ---------------------------------------------------------------------------
# Synthetic call-history seed
# ---------------------------------------------------------------------------
# 40 completed call records spread across the last 14 days.  All run_ids are
# prefixed "seed-" so real test calls are never confused with seed rows and
# the idempotency check (see seed_calls) can target exactly this prefix.
#
# Urgency tiers for the load pool (ceiling multipliers):
#   LD-001, LD-002, LD-010  ->  <=2 days  ->  8%
#   LD-008, LD-003, LD-004  ->   3-5 days ->  6%
#   LD-005, LD-006, LD-007, LD-009  ->  >5 days  ->  4%
#
# final_rate for booked rows stays within the urgency ceiling for that load.
# Negotiated rows include matching negotiation_events (1-3 rounds).
# After-hours timestamps (~22% of records): before 7am or after 7pm,
# or on a weekend day.


def _ts(days_ago: int, hour: int, minute: int = 0) -> datetime:
    """Naive UTC datetime days_ago before today at hour:minute."""
    d = date.today() - timedelta(days=days_ago)
    return datetime(d.year, d.month, d.day, hour, minute)


# loadboard_rate by load_id (mirrors SEED_LOADS, avoids a runtime lookup)
_LOADBOARD_RATE: dict[str, float] = {
    "LD-001": 1250.0,
    "LD-002": 2100.0,
    "LD-003": 3200.0,
    "LD-004": 950.0,
    "LD-005": 2800.0,
    "LD-006": 1800.0,
    "LD-007": 1650.0,
    "LD-008": 2400.0,
    "LD-009": 2100.0,
    "LD-010": 2750.0,
}

# Carrier pool
_CARRIERS = [
    ("288570", "ACME FREIGHT LLC"),
    ("112233", "BLUE RIDGE TRANSPORT INC"),
    ("445566", "HEARTLAND EXPRESS"),
    ("778899", "LONE STAR CARRIERS LLC"),
    ("334455", "PACIFIC COAST LOGISTICS"),
    ("667788", "GREAT LAKES FREIGHT CO"),
    ("990011", "MIDWEST MOVING INC"),
    ("223344", "SOUTHERN ROUTE CARRIERS"),
    ("556677", "ROCKIES TRANSPORT LLC"),
    ("889900", "SUNRISE LOGISTICS INC"),
]


def _carrier(i: int) -> tuple[str, str]:
    return _CARRIERS[i % len(_CARRIERS)]


# Each record: (run_id_suffix, days_ago, hour, minute, outcome, sentiment,
#               load_id, final_rate, duration, is_negotiated, neg_rounds)
# is_negotiated=True -> generate negotiation_events rows
# neg_rounds: how many rounds completed (1-3); last round determines final_rate
_SEED_CALLS_SPEC: list[tuple] = [
    # --- booked, negotiated (22 rows) ---
    ("001", 0,  14, 22, "booked", "positive",   "LD-001", 1275.0, 245, True,  2),
    ("002", 0,  10, 5,  "booked", "positive",   "LD-002", 2142.0, 210, True,  1),
    ("003", 1,  9,  15, "booked", "positive",   "LD-010", 2805.0, 280, True,  2),
    ("004", 1,  15, 40, "booked", "positive",   "LD-008", 2448.0, 260, True,  2),
    ("005", 2,  11, 0,  "booked", "positive",   "LD-003", 3264.0, 300, True,  2),
    ("006", 2,  16, 30, "booked", "positive",   "LD-004", 969.0,  230, True,  1),
    ("007", 3,  8,  45, "booked", "positive",   "LD-005", 2856.0, 270, True,  2),
    ("008", 3,  13, 20, "booked", "positive",   "LD-006", 1836.0, 255, True,  2),
    ("009", 4,  10, 10, "booked", "positive",   "LD-007", 1683.0, 240, True,  1),
    ("010", 4,  14, 50, "booked", "positive",   "LD-009", 2142.0, 265, True,  2),
    ("011", 5,  9,  0,  "booked", "positive",   "LD-001", 1300.0, 290, True,  3),
    ("012", 5,  17, 30, "booked", "neutral",    "LD-002", 2121.0, 220, True,  1),
    ("013", 6,  11, 15, "booked", "positive",   "LD-010", 2860.0, 275, True,  3),
    ("014", 6,  15, 0,  "booked", "positive",   "LD-008", 2472.0, 250, True,  2),
    ("015", 7,  10, 30, "booked", "neutral",    "LD-003", 3200.0, 195, True,  2),
    ("016", 7,  6,  45, "booked", "positive",   "LD-004", 950.0,  180, True,  1),  # after-hours
    ("017", 8,  8,  0,  "booked", "positive",   "LD-005", 2912.0, 285, True,  3),
    ("018", 8,  12, 40, "booked", "neutral",    "LD-006", 1800.0, 165, True,  1),
    ("019", 9,  9,  20, "booked", "positive",   "LD-007", 1650.0, 155, True,  1),
    ("020", 9,  14, 0,  "booked", "positive",   "LD-009", 2163.0, 265, True,  2),
    ("021", 10, 11, 0,  "booked", "positive",   "LD-001", 1260.0, 210, True,  1),
    ("022", 10, 16, 15, "booked", "neutral",    "LD-002", 2100.0, 140, False, 0),  # posted rate
    # --- booked at posted rate, no negotiation (0 rounds) ---
    ("023", 11, 10, 0,  "booked", "positive",   "LD-010", 2750.0, 130, False, 0),
    ("024", 11, 20, 0,  "booked", "positive",   "LD-008", 2400.0, 125, False, 0),  # after-hours
    ("025", 12, 7,  30, "booked", "positive",   "LD-003", 3200.0, 135, False, 0),  # after-hours
    ("026", 12, 11, 0,  "booked", "neutral",    "LD-004", 950.0,  120, False, 0),
    ("027", 13, 9,  0,  "booked", "positive",   "LD-005", 2800.0, 128, False, 0),
    ("028", 13, 13, 0,  "booked", "positive",   "LD-006", 1800.0, 118, False, 0),
    # --- negotiation_failed (6 rows) ---
    ("029", 1,  10, 30, "negotiation_failed", "negative", "LD-001", None, 195, True,  3),
    ("030", 3,  14, 0,  "negotiation_failed", "neutral",  "LD-002", None, 180, True,  3),
    ("031", 5,  9,  15, "negotiation_failed", "negative", "LD-008", None, 210, True,  3),
    ("032", 7,  11, 0,  "negotiation_failed", "negative", "LD-003", None, 220, True,  3),
    ("033", 10, 8,  30, "negotiation_failed", "neutral",  "LD-009", None, 175, True,  3),
    ("034", 13, 6,  0,  "negotiation_failed", "negative", "LD-005", None, 185, True,  3),  # after-hours
    # --- carrier_ineligible (3 rows) ---
    ("035", 2,  10, 0,  "carrier_ineligible", "neutral",  None,    None, 55,  False, 0),
    ("036", 6,  14, 30, "carrier_ineligible", "negative", None,    None, 48,  False, 0),
    ("037", 11, 9,  0,  "carrier_ineligible", "neutral",  None,    None, 60,  False, 0),
    # --- load_not_found (3 rows) ---
    ("038", 0,  19, 45, "load_not_found", "neutral",  None, None, 75,  False, 0),  # after-hours
    ("039", 4,  10, 0,  "load_not_found", "neutral",  None, None, 80,  False, 0),
    ("040", 9,  11, 30, "load_not_found", "negative", None, None, 70,  False, 0),
    # --- not_interested (3 rows) ---
    ("041", 1,  13, 0,  "not_interested", "neutral",  "LD-007", None, 95,  False, 0),
    ("042", 6,  8,  0,  "not_interested", "negative", "LD-006", None, 88,  False, 0),
    ("043", 12, 21, 0,  "not_interested", "negative", "LD-004", None, 92,  False, 0),  # after-hours
    # --- equipment_mismatch (2 rows) ---
    ("044", 3,  10, 30, "equipment_mismatch", "neutral", "LD-002", None, 65,  False, 0),
    ("045", 8,  14, 0,  "equipment_mismatch", "neutral", "LD-003", None, 70,  False, 0),
    # --- transferred_to_human (1 row) ---
    ("046", 5,  11, 0,  "transferred_to_human", "neutral", "LD-009", None, 110, False, 0),
]


def _build_neg_events(
    run_id: str,
    load_id: str,
    final_rate: float | None,
    outcome: str,
    num_rounds: int,
    base_ts: datetime,
) -> list[NegotiationEvent]:
    """Generate realistic negotiation_events for a call.

    For booked calls: last event is 'accept' at final_rate.
    For negotiation_failed calls: all events are 'counter'/'final' decisions, last is 'final'.
    """
    rate = _LOADBOARD_RATE[load_id]
    # Urgency ceiling (use band=8% as conservative proxy; exact tier doesn't matter
    # for seed data since final_rate is already clamped when defined above)
    ceiling = rate * 1.08  # conservative upper bound for fake event prices

    events: list[NegotiationEvent] = []
    for r in range(1, num_rounds + 1):
        is_last = r == num_rounds
        ts = base_ts + timedelta(minutes=r * 2)

        if outcome == "booked" and is_last:
            decision = "accept"
            agent_price = final_rate  # type: ignore[arg-type]
            carrier_offer = final_rate  # carrier offered exactly this
        elif is_last:
            # negotiation_failed: last round is 'final' (ceiling offer, carrier walked)
            decision = "final"
            agent_price = min(round(ceiling / 25) * 25, ceiling)
            carrier_offer = agent_price * 1.05  # carrier asked more than ceiling
        else:
            # intermediate counters
            band = ceiling - rate
            step_pct = 0.60 if r == 1 else 0.85
            agent_price = min(round((rate + step_pct * band) / 25) * 25, ceiling)
            carrier_offer = agent_price * 1.02  # carrier slightly above step
            decision = "counter"

        events.append(NegotiationEvent(
            run_id=run_id,
            round=r,
            load_id=load_id,
            carrier_offer=round(carrier_offer, 2),
            agent_price=round(agent_price, 2),
            decision=decision,
            created_at=ts,
        ))
    return events


async def seed_calls(session: AsyncSession | None = None) -> None:
    """Insert 40 synthetic call records (+ matching negotiation_events) if not already present.

    Idempotent: skips entirely when any row with run_id prefix 'seed-' exists.
    Delete those rows (or the whole DB) to reseed.
    """
    owns_session = session is None
    if owns_session:
        from app.db.database import _init_engine
        from sqlalchemy.ext.asyncio import async_sessionmaker
        _, maker = _init_engine()
        session = maker()

    try:
        existing = await session.execute(
            select(Call).where(Call.run_id.like("seed-%")).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            return

        for i, spec in enumerate(_SEED_CALLS_SPEC):
            (
                suffix, days_ago, hour, minute, outcome, sentiment,
                load_id, final_rate, duration, is_negotiated, neg_rounds,
            ) = spec

            run_id = f"seed-{suffix}"
            mc_number, carrier_name = _carrier(i)
            carrier_eligible = outcome != "carrier_ineligible"
            created = _ts(days_ago, hour, minute)
            rounds_val = neg_rounds if neg_rounds > 0 else None

            call = Call(
                run_id=run_id,
                mc_number=mc_number,
                carrier_name=carrier_name,
                carrier_eligible=carrier_eligible,
                load_id=load_id,
                outcome=outcome,
                outcome_source="classified",
                sentiment=sentiment,
                final_rate=final_rate,
                rounds=rounds_val,
                duration=float(duration),
                run_url=None,
                created_at=created,
                updated_at=created,
            )
            session.add(call)

            if is_negotiated and neg_rounds > 0 and load_id is not None:
                events = _build_neg_events(
                    run_id=run_id,
                    load_id=load_id,
                    final_rate=final_rate,
                    outcome=outcome,
                    num_rounds=neg_rounds,
                    base_ts=created,
                )
                for ev in events:
                    session.add(ev)

        await session.commit()
    finally:
        if owns_session:
            await session.close()
