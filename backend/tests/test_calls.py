"""Tests for POST /calls upsert endpoint."""
import pytest

VALID = {"X-API-Key": "test-api-key-abc123"}


@pytest.mark.asyncio
async def test_new_call_creates_row(client):
    resp = await client.post(
        "/calls",
        json={
            "run_id": "run-001",
            "mc_number": "288570",
            "carrier_name": "ACME FREIGHT",
            "outcome": "booked",
            "sentiment": "positive",
            "final_rate": 1300.0,
            "duration": 180.0,
        },
        headers=VALID,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == "run-001"
    assert data["mc_number"] == "288570"
    assert data["carrier_name"] == "ACME FREIGHT"
    assert data["outcome"] == "booked"
    assert data["outcome_source"] == "classified"  # defaulted
    assert data["sentiment"] == "positive"
    assert data["final_rate"] == 1300.0
    assert data["duration"] == 180.0
    assert data["rounds"] is None  # no negotiation_events yet
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


@pytest.mark.asyncio
async def test_second_post_updates_non_null_fields_only(client):
    # First create
    await client.post(
        "/calls",
        json={"run_id": "run-002", "mc_number": "111111", "sentiment": "neutral"},
        headers=VALID,
    )
    # Second update — only sentiment and duration provided; mc_number must survive
    resp = await client.post(
        "/calls",
        json={"run_id": "run-002", "sentiment": "positive", "duration": 240.0},
        headers=VALID,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mc_number"] == "111111"   # existing value preserved
    assert data["sentiment"] == "positive"  # updated
    assert data["duration"] == 240.0        # new field written


@pytest.mark.asyncio
async def test_resolved_outcome_not_overwritten_by_classified(client):
    # Create with a resolved outcome
    await client.post(
        "/calls",
        json={"run_id": "run-003", "outcome": "booked", "outcome_source": "resolved"},
        headers=VALID,
    )
    # Attempt overwrite with classified
    resp = await client.post(
        "/calls",
        json={
            "run_id": "run-003",
            "outcome": "no_match",
            "outcome_source": "classified",
        },
        headers=VALID,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["outcome"] == "booked"          # resolved outcome preserved
    assert data["outcome_source"] == "resolved"  # source preserved


@pytest.mark.asyncio
async def test_rounds_reflects_negotiation_events(client):
    from app.db.database import get_db
    from app.db.models import NegotiationEvent
    from app.main import app

    # Use the test-overridden session so events land in the same DB the endpoint queries
    async for db in app.dependency_overrides[get_db]():
        db.add(NegotiationEvent(
            run_id="run-004", round=1, load_id="LD-001",
            carrier_offer=1300.0, agent_price=1275.0, decision="counter",
        ))
        db.add(NegotiationEvent(
            run_id="run-004", round=2, load_id="LD-001",
            carrier_offer=1280.0, agent_price=1280.0, decision="accept",
        ))
        await db.commit()
        break

    resp = await client.post(
        "/calls",
        json={"run_id": "run-004", "outcome": "booked"},
        headers=VALID,
    )
    assert resp.status_code == 200
    assert resp.json()["rounds"] == 2


@pytest.mark.asyncio
async def test_carrier_eligible_string_true_coerced(client):
    resp = await client.post(
        "/calls",
        json={"run_id": "run-elig-01", "carrier_eligible": "true"},
        headers=VALID,
    )
    assert resp.status_code == 200
    assert resp.json()["carrier_eligible"] is True


@pytest.mark.asyncio
async def test_carrier_eligible_bool_true(client):
    resp = await client.post(
        "/calls",
        json={"run_id": "run-elig-02", "carrier_eligible": True},
        headers=VALID,
    )
    assert resp.status_code == 200
    assert resp.json()["carrier_eligible"] is True


@pytest.mark.asyncio
async def test_carrier_eligible_string_false_coerced(client):
    resp = await client.post(
        "/calls",
        json={"run_id": "run-elig-03", "carrier_eligible": "false"},
        headers=VALID,
    )
    assert resp.status_code == 200
    assert resp.json()["carrier_eligible"] is False


@pytest.mark.asyncio
async def test_carrier_eligible_missing_is_none(client):
    resp = await client.post(
        "/calls",
        json={"run_id": "run-elig-04"},
        headers=VALID,
    )
    assert resp.status_code == 200
    assert resp.json()["carrier_eligible"] is None


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(client):
    resp = await client.post("/calls", json={"run_id": "run-x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_wrong_api_key_returns_401(client):
    resp = await client.post(
        "/calls", json={"run_id": "run-x"}, headers={"X-API-Key": "bad"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_missing_run_id_returns_422(client):
    resp = await client.post(
        "/calls", json={"outcome": "booked"}, headers=VALID
    )
    assert resp.status_code == 422
