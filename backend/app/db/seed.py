from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Load


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
