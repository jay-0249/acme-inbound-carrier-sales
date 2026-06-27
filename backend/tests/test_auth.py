"""API-key auth: two-scope model (read key vs. full key)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

TEST_FULL_KEY = "test-api-key-abc123"   # LOADS_API_KEY — write + read
TEST_READ_KEY = "test-read-key-xyz789"  # READ_API_KEY  — read only

FULL_HEADERS = {"X-API-Key": TEST_FULL_KEY}
READ_HEADERS = {"X-API-Key": TEST_READ_KEY}


# ---------------------------------------------------------------------------
# Existing: full key passes, missing/wrong key -> 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_key_passes(client):
    response = await client.get("/loads", headers=FULL_HEADERS)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_missing_key_returns_401(client):
    response = await client.get("/loads")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_wrong_key_returns_401(client):
    response = await client.get("/loads", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_missing_key_on_single_load_returns_401(client):
    response = await client.get("/loads/LD-001")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_wrong_key_on_single_load_returns_401(client):
    response = await client.get("/loads/LD-001", headers={"X-API-Key": "bad"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Read key accepted on read-only endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_read_key_accepted_on_loads(client):
    response = await client.get("/loads", headers=READ_HEADERS)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_read_key_accepted_on_single_load(client):
    response = await client.get("/loads/LD-001", headers=READ_HEADERS)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_read_key_accepted_on_metrics(client):
    response = await client.get("/metrics", headers=READ_HEADERS)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_read_key_accepted_on_verify_carrier(client):
    fmcsa_resp = MagicMock()
    fmcsa_resp.raise_for_status = MagicMock()
    fmcsa_resp.json.return_value = {"content": []}
    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=fmcsa_resp)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)
    with patch("app.api.carrier.httpx.AsyncClient", return_value=mock_http):
        response = await client.get("/verify-carrier/123456", headers=READ_HEADERS)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Read key REJECTED on write endpoints (401)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_read_key_rejected_on_post_calls(client):
    response = await client.post(
        "/calls",
        json={"run_id": "auth-test-calls-001"},
        headers=READ_HEADERS,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_read_key_rejected_on_post_negotiate(client):
    response = await client.post(
        "/negotiate",
        json={"run_id": "auth-test-neg-001", "load_id": "LD-001", "carrier_offer": 1200.0},
        headers=READ_HEADERS,
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Full key accepted on write endpoints (superset of read)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_key_accepted_on_post_calls(client):
    response = await client.post(
        "/calls",
        json={"run_id": "auth-test-calls-full-001"},
        headers=FULL_HEADERS,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_full_key_accepted_on_post_negotiate(client):
    response = await client.post(
        "/negotiate",
        json={"run_id": "auth-test-neg-full-001", "load_id": "LD-001", "carrier_offer": 1200.0},
        headers=FULL_HEADERS,
    )
    # 200 (counter or accept) — not 401
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Missing key -> 401 on write endpoints too
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_key_on_post_calls_returns_401(client):
    response = await client.post("/calls", json={"run_id": "x"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_missing_key_on_post_negotiate_returns_401(client):
    response = await client.post(
        "/negotiate",
        json={"run_id": "x", "load_id": "LD-001", "carrier_offer": 1200.0},
    )
    assert response.status_code == 401
