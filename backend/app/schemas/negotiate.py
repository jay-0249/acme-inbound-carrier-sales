from typing import Optional

from pydantic import BaseModel, Field


class NegotiateRequest(BaseModel):
    run_id: str
    load_id: str
    carrier_offer: float = Field(gt=0, description="Carrier's offered rate in USD; must be > 0")


class NegotiateResponse(BaseModel):
    run_id: str
    round: int               # server-derived; never from the agent
    decision: str            # "accept" | "counter" | "final" | "confirm_offer"
    agent_price: Optional[float] = None  # null for confirm_offer
    ceiling: float           # urgency-scaled ceiling, exposed for observability
    negotiation_status: str  # "negotiating" | "ceiling_reached" | "needs_confirmation"
    message: Optional[str] = None  # set for confirm_offer; null for normal decisions
