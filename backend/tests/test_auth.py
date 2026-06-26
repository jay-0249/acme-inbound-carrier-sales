"""API-key authentication on every endpoint."""
import pytest


@pytest.mark.asyncio
async def test_valid_key_passes(client):
    response = await client.get("/loads", headers={"X-API-Key": "test-api-key-abc123"})
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
