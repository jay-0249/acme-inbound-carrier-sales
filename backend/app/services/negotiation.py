"""
Deterministic negotiation logic. No DB access, no LLM calls.
All money decisions live here so they are independently testable.

Future extension points (decided server-side, NEVER supplied by the agent):
  - strategy: "front_loaded" (default) | "flat" | "aggressive" — ladder shape.
  - sentiment: "positive" | "neutral" | "negative" — could tighten/loosen band.
These are server-owned signals; the agent only ever sends carrier_offer.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class NegotiationResult:
    decision: str           # "accept" | "counter" | "final"
    agent_price: float
    ceiling: float
    negotiation_status: str  # "negotiating" | "ceiling_reached"


def compute_ceiling(loadboard_rate: float, days_to_pickup: int) -> float:
    """Urgency-scaled ceiling. Negative days (past pickup) treated as <= 2."""
    if days_to_pickup <= 2:
        return loadboard_rate * 1.08
    elif days_to_pickup <= 5:
        return loadboard_rate * 1.06
    return loadboard_rate * 1.04


def _round25(value: float) -> float:
    return round(value / 25) * 25


def _raw_step(loadboard_rate: float, ceiling: float, round_num: int) -> float:
    """Unrounded front-loaded ladder step."""
    band = ceiling - loadboard_rate
    if round_num == 1:
        return loadboard_rate + 0.60 * band
    elif round_num == 2:
        return loadboard_rate + 0.85 * band
    return ceiling  # round >= 3: go to ceiling


def negotiate(
    *,
    carrier_offer: float,
    loadboard_rate: float,
    pickup_date: date,
    round_num: int,
    today: Optional[date] = None,
) -> NegotiationResult:
    if today is None:
        today = date.today()

    days = (pickup_date - today).days
    ceiling = compute_ceiling(loadboard_rate, days)

    # Rounded step (before any decision)
    step = _round25(_raw_step(loadboard_rate, ceiling, round_num))

    if carrier_offer <= step:
        decision = "accept"
        # Exact carrier price — never pay more than asked, no rounding applied.
        agent_price = carrier_offer
    elif round_num < 3:
        decision = "counter"
        agent_price = step
        # Guardrail: absolute ceiling clamp, independent of ladder math.
        agent_price = min(agent_price, ceiling)
    else:
        decision = "final"
        agent_price = _round25(ceiling)
        # Guardrail re-applied after rounding (last line of defense).
        agent_price = min(agent_price, ceiling)

    negotiation_status = "ceiling_reached" if decision == "final" else "negotiating"
    return NegotiationResult(
        decision=decision,
        agent_price=agent_price,
        ceiling=ceiling,
        negotiation_status=negotiation_status,
    )
