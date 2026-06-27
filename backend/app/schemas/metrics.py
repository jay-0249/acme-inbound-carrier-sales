from typing import Optional

from pydantic import BaseModel


class CapacityMetrics(BaseModel):
    calls_handled: int
    calls_after_hours: int
    calls_missed: int
    booking_rate: float
    loads_booked: int
    automation_rate: float


class ValueModel(BaseModel):
    rep_hours_freed: float
    assumed_loaded_wage_per_hour: float
    assumed_agent_cost_per_call: float
    value_captured_usd: float


class UrgencyTierMetric(BaseModel):
    tier: str
    avg_pct_over_loadboard: float   # realized — need not be monotonic
    ceiling_multiplier: float        # designed ceiling (1.08 / 1.06 / 1.04)
    loads: int


class MarginMetrics(BaseModel):
    avg_pct_over_loadboard: float
    total_dollars_over_loadboard: float
    by_urgency_tier: list[UrgencyTierMetric]


class OutcomeCount(BaseModel):
    outcome: str
    count: int
    pct: float


class TopDeclineReason(BaseModel):
    outcome: str
    count: int


class SentimentCounts(BaseModel):
    positive: int
    neutral: int
    negative: int


class NegotiationMetrics(BaseModel):
    avg_rounds_to_close: float
    settled_distribution: dict[str, int]


class RecentCall(BaseModel):
    run_id: str
    carrier_name: Optional[str]
    load_id: Optional[str]
    outcome: Optional[str]
    sentiment: Optional[str]
    final_rate: Optional[float]
    loadboard_rate: Optional[float]
    pct_over_loadboard: Optional[float]
    rounds: Optional[int]
    created_at: str
    run_url: Optional[str]


class MetricsResponse(BaseModel):
    capacity: CapacityMetrics
    value_model: ValueModel
    margin: MarginMetrics
    outcomes: list[OutcomeCount]
    top_decline_reason: TopDeclineReason
    sentiment: SentimentCounts
    negotiation: NegotiationMetrics
    recent_calls: list[RecentCall]
