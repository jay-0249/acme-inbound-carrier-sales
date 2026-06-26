"""Tests for GET /verify-carrier/{mc_number}. Never calls the real FMCSA API."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_fmcsa_response(content: list) -> MagicMock:
    """Return a mock httpx Response whose .json() yields the given content list."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"content": content}
    return resp


def _make_http_client(response: MagicMock) -> MagicMock:
    """Wrap a mock response in a mock AsyncClient context manager."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


VALID_HEADERS = {"X-API-Key": "test-api-key-abc123"}


@pytest.mark.asyncio
async def test_eligible_carrier_returns_true(client):
    fmcsa_resp = _make_fmcsa_response(
        [
            {
                "carrier": {
                    "allowedToOperate": "Y",
                    "legalName": "ACME FREIGHT INC",
                    "dbaName": "ACME",
                    "dotNumber": "1234567",
                }
            }
        ]
    )
    with patch("app.api.carrier.httpx.AsyncClient", return_value=_make_http_client(fmcsa_resp)):
        response = await client.get("/verify-carrier/123456", headers=VALID_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] is True
    assert data["carrier_name"] == "ACME FREIGHT INC"
    assert data["dot_number"] == "1234567"
    assert data["mc_number"] == "123456"


@pytest.mark.asyncio
async def test_empty_content_returns_not_eligible(client):
    fmcsa_resp = _make_fmcsa_response([])
    with patch("app.api.carrier.httpx.AsyncClient", return_value=_make_http_client(fmcsa_resp)):
        response = await client.get("/verify-carrier/999999", headers=VALID_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] is False
    assert data["carrier_name"] is None
    assert data["dot_number"] is None
    assert data["mc_number"] == "999999"


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(client):
    response = await client.get("/verify-carrier/123456")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_api_key_returns_401(client):
    response = await client.get("/verify-carrier/123456", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401
