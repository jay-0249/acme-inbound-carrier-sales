from pydantic import BaseModel


class CarrierVerifyResponse(BaseModel):
    mc_number: str
    eligible: bool
    carrier_name: str | None
    dot_number: str | None
