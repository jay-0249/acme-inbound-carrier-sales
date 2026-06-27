import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.security import verify_read_access
from app.schemas.carrier import CarrierVerifyResponse

router = APIRouter(tags=["carrier"])

_FMCSA_DOCKET_URL = (
    "https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}"
    "?webKey={web_key}"
)


@router.get("/verify-carrier/{mc_number}", response_model=CarrierVerifyResponse)
async def verify_carrier(
    mc_number: str,
    settings: Settings = Depends(get_settings),
    _: str = Depends(verify_read_access),
) -> CarrierVerifyResponse:
    # FMCSA docket-number lookup accepts only the numeric portion; strip the "MC-" or "MC"
    # prefix that the voice agent or caller may include (e.g. "MC-288570" -> "288570").
    stripped = mc_number.strip()
    upper = stripped.upper()
    if upper.startswith("MC-"):
        numeric_mc = stripped[3:]
    elif upper.startswith("MC"):
        numeric_mc = stripped[2:]
    else:
        numeric_mc = stripped
    url = _FMCSA_DOCKET_URL.format(mc_number=numeric_mc, web_key=settings.FMCSA_API_KEY)
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            resp = await http.get(url)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.RequestError, httpx.HTTPStatusError):
        raise HTTPException(status_code=502, detail="FMCSA request failed")

    content = data.get("content") or []
    if not content:
        return CarrierVerifyResponse(
            mc_number=mc_number,
            eligible=False,
            carrier_name=None,
            dot_number=None,
        )

    # If this docket response is thin, a follow-up GET to
    # /qc/services/carriers/{dotNumber} would enrich with safety/insurance data.
    carrier = content[0].get("carrier") or {}
    eligible = carrier.get("allowedToOperate") == "Y"
    carrier_name = carrier.get("legalName") or carrier.get("dbaName") or None
    raw_dot = carrier.get("dotNumber")
    dot_number = str(raw_dot) if raw_dot is not None else None

    return CarrierVerifyResponse(
        mc_number=mc_number,
        eligible=eligible,
        carrier_name=carrier_name,
        dot_number=dot_number,
    )
