from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LoadResponse(BaseModel):
    load_id: str
    origin: str
    destination: str
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str
    loadboard_rate: float
    notes: Optional[str] = None
    weight: int
    commodity_type: str
    num_of_pieces: int
    miles: int
    dimensions: Optional[str] = None

    model_config = {"from_attributes": True}
