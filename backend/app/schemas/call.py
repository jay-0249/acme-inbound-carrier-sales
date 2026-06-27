from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class CallCreate(BaseModel):
    run_id: str
    carrier_eligible: Optional[bool] = None
    outcome: Optional[str] = None
    outcome_source: Optional[str] = None
    sentiment: Optional[str] = None
    duration: Optional[float] = None
    run_url: Optional[str] = None
    mc_number: Optional[str] = None
    carrier_name: Optional[str] = None
    load_id: Optional[str] = None
    final_rate: Optional[float] = None

    @field_validator("carrier_eligible", mode="before")
    @classmethod
    def coerce_eligible(cls, v: object) -> Optional[bool]:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            lower = v.strip().lower()
            if lower == "true":
                return True
            if lower == "false":
                return False
        return None


class CallResponse(BaseModel):
    run_id: str
    mc_number: Optional[str]
    carrier_name: Optional[str]
    carrier_eligible: Optional[bool]
    load_id: Optional[str]
    outcome: Optional[str]
    outcome_source: Optional[str]
    sentiment: Optional[str]
    final_rate: Optional[float]
    rounds: Optional[int]
    duration: Optional[float]
    run_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
