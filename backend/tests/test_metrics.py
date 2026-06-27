"""Tests for GET /metrics and synthetic call-history seed."""
import pytest

from app.db.models import Call, Load, NegotiationEvent
from app.db.seed import seed_calls

VALID = {"X-API-Key": "test-api-key-abc123"}


# ---------------------------------------------------------------------------
# Seed idempotency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_calls_idempotent(client):
    """Running seed_calls twice must not duplicate seed rows."""
    from app.db.database import get_db
    from app.main import app
    from sqlalchemy import func, select

    # Seed once (conftest does NOT seed calls; we do it here)
    async for db in app.dependency_overrides[get_db]():
        await seed_calls(db)
        break

    # Count after first seed
    async for db in app.dependency_overrides[get_db]():
        first_count = (
            await db.execute(
                select(func.count()).select_from(Call).where(Call.run_id.like("seed-%"))
            )
        ).scalar_one()
        break

    # Seed again
    async for db in app.dependency_overrides[get_db]():
        await seed_calls(db)
        break

    # Count must be unchanged
    async for db in app.dependency_overrides[get_db]():
        second_count = (
            await db.execute(
                select(func.count()).select_from(Call).where(Call.run_id.like("seed-%"))
            )
        ).scalar_one()
        break

    assert first_count == second_count
    assert first_count > 0


@pytest.mark.asyncio
async def test_seed_rows_prefixed(client):
    """All synthetic call rows must have run_id starting with 'seed-'."""
    from app.db.database import get_db
    from app.main import app
    from sqlalchemy import select

    async for db in app.dependency_overrides[get_db]():
        await seed_calls(db)
        rows = list((await db.execute(select(Call))).scalars().all())
        break

    seed_rows = [r for r in rows if r.run_id.startswith("seed-")]
    assert len(seed_rows) > 0
    non_seed = [r for r in rows if not r.run_id.startswith("seed-")]
    assert len(non_seed) == 0  # only seed rows in a fresh test DB


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metrics_missing_key_returns_401(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_metrics_wrong_key_returns_401(client):
    resp = await client.get("/metrics", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Empty DB — no division-by-zero
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metrics_empty_db_returns_200(client):
    """With zero call records every rate metric must default to 0, not crash."""
    resp = await client.get("/metrics", headers=VALID)
    assert resp.status_code == 200
    data = resp.json()
    assert data["capacity"]["calls_handled"] == 0
    assert data["capacity"]["booking_rate"] == 0.0
    assert data["capacity"]["automation_rate"] == 0.0
    assert data["margin"]["avg_pct_over_loadboard"] == 0.0
    assert data["negotiation"]["avg_rounds_to_close"] == 0.0
    assert data["recent_calls"] == []


# ---------------------------------------------------------------------------
# Helpers: seed calls into the test DB
# ---------------------------------------------------------------------------

async def _seed(client):
    from app.db.database import get_db
    from app.main import app
    async for db in app.dependency_overrides[get_db]():
        await seed_calls(db)
        break


# ---------------------------------------------------------------------------
# Shape validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metrics_full_shape(client):
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    assert resp.status_code == 200
    data = resp.json()

    cap = data["capacity"]
    for key in ("calls_handled", "calls_after_hours", "calls_missed",
                "booking_rate", "loads_booked", "automation_rate"):
        assert key in cap

    vm = data["value_model"]
    for key in ("rep_hours_freed", "assumed_loaded_wage_per_hour",
                "assumed_agent_cost_per_call", "value_captured_usd"):
        assert key in vm

    mg = data["margin"]
    assert "avg_pct_over_loadboard" in mg
    assert "total_dollars_over_loadboard" in mg
    tiers = mg["by_urgency_tier"]
    assert len(tiers) == 3
    tier_labels = {t["tier"] for t in tiers}
    assert "<=2 days (8%)" in tier_labels
    assert "3-5 days (6%)" in tier_labels
    assert ">5 days (4%)" in tier_labels

    assert isinstance(data["outcomes"], list)
    assert len(data["outcomes"]) > 0
    assert "outcome" in data["top_decline_reason"]

    sent = data["sentiment"]
    for key in ("positive", "neutral", "negative"):
        assert key in sent

    neg = data["negotiation"]
    assert "avg_rounds_to_close" in neg
    assert set(neg["settled_distribution"].keys()) == {"round_1", "round_2", "round_3", "walked"}

    assert isinstance(data["recent_calls"], list)


# ---------------------------------------------------------------------------
# Metric correctness
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_booking_rate(client):
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    cap = data["capacity"]
    total = cap["calls_handled"]
    booked = cap["loads_booked"]
    assert total > 0
    assert cap["booking_rate"] == pytest.approx(booked / total, rel=1e-4)


@pytest.mark.asyncio
async def test_automation_rate_no_transferred_calls(client):
    """With only automated outcomes, automation_rate should be 1.0."""
    from app.db.database import get_db
    from app.main import app

    async for db in app.dependency_overrides[get_db]():
        db.add(Call(
            run_id="am-001", outcome="booked", outcome_source="classified",
            sentiment="positive", final_rate=1250.0, duration=180.0,
        ))
        db.add(Call(
            run_id="am-002", outcome="negotiation_failed", outcome_source="classified",
            sentiment="neutral", duration=120.0,
        ))
        await db.commit()
        break

    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    assert data["capacity"]["automation_rate"] == 1.0


@pytest.mark.asyncio
async def test_automation_rate_with_transfer(client):
    """A single transferred_to_human call must lower automation_rate below 1."""
    from app.db.database import get_db
    from app.main import app

    async for db in app.dependency_overrides[get_db]():
        for rid, outcome in [("aut-a", "booked"), ("aut-b", "transferred_to_human")]:
            db.add(Call(
                run_id=rid, outcome=outcome, outcome_source="classified",
                sentiment="neutral", duration=60.0,
            ))
        await db.commit()
        break

    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    assert data["capacity"]["automation_rate"] == pytest.approx(0.5, rel=1e-4)


@pytest.mark.asyncio
async def test_sentiment_counts_sum_to_total(client):
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    sent = data["sentiment"]
    total = data["capacity"]["calls_handled"]
    assert sent["positive"] + sent["neutral"] + sent["negative"] == total


@pytest.mark.asyncio
async def test_outcomes_sum_to_total(client):
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    total = data["capacity"]["calls_handled"]
    assert sum(o["count"] for o in data["outcomes"]) == total


@pytest.mark.asyncio
async def test_top_decline_reason_is_not_booked(client):
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    assert data["top_decline_reason"]["outcome"] != "booked"
    assert data["top_decline_reason"]["count"] > 0


@pytest.mark.asyncio
async def test_margin_by_urgency_tier_within_bands(client):
    """avg_pct_over_loadboard per tier must not exceed the ceiling multiplier - 1."""
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    tiers = {t["tier"]: t for t in data["margin"]["by_urgency_tier"]}

    # Urgency tiers: <=2 days (<=8%), 3-5 days (<=6%), >5 days (<=4%)
    # Some bookings are at posted rate (0% over), so the averages are lower.
    for label, cap in [
        ("<=2 days (8%)", 0.08),
        ("3-5 days (6%)", 0.06),
        (">5 days (4%)", 0.04),
    ]:
        if tiers[label]["loads"] > 0:
            assert tiers[label]["avg_pct_over_loadboard"] <= cap + 1e-6, (
                f"{label}: {tiers[label]['avg_pct_over_loadboard']} > {cap}"
            )


@pytest.mark.asyncio
async def test_recent_calls_newest_first_and_capped(client):
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    recent = data["recent_calls"]
    assert len(recent) <= 25
    if len(recent) > 1:
        for i in range(len(recent) - 1):
            assert recent[i]["created_at"] >= recent[i + 1]["created_at"]


@pytest.mark.asyncio
async def test_recent_calls_has_expected_fields(client):
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    for rc in data["recent_calls"]:
        for field in ("run_id", "carrier_name", "load_id", "outcome",
                      "sentiment", "final_rate", "loadboard_rate",
                      "pct_over_loadboard", "rounds", "created_at", "run_url"):
            assert field in rc


@pytest.mark.asyncio
async def test_calls_after_hours_count(client):
    """After-hours calls in seed data: verify count is non-zero (spec ~20-25%)."""
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    assert data["capacity"]["calls_after_hours"] > 0


@pytest.mark.asyncio
async def test_negotiation_avg_rounds_positive_when_events_present(client):
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    neg = data["negotiation"]
    assert neg["avg_rounds_to_close"] > 0
    dist = neg["settled_distribution"]
    total_settled = sum(dist.values())
    assert total_settled > 0
