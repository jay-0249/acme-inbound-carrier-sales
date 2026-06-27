from pydantic import BaseModel, Field


class NegotiateRequest(BaseModel):
    run_id: str
    load_id: str
    carrier_offer: float = Field(gt=0, description="Carrier's offered rate in USD; must be > 0")


class NegotiateResponse(BaseModel):
    run_id: str
    round: int              # server-derived; never from the agent
    decision: str           # "accept" | "counter" | "final"
    agent_price: float      # the number the agent should say
    ceiling: float          # urgency-scaled ceiling, exposed for observability
    negotiation_status: str  # "negotiating" | "ceiling_reached"
