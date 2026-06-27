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
    for t in tiers:
        assert "ceiling_multiplier" in t

    assert isinstance(data["outcomes"], list)
    assert len(data["outcomes"]) > 0
    assert "outcome" in data["top_decline_reason"]

    sent = data["sentiment"]
    for group in ("overall", "booked", "not_booked"):
        assert group in sent, f"sentiment missing '{group}'"
        for key in ("positive", "neutral", "negative"):
            assert key in sent[group], f"sentiment.{group} missing '{key}'"

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
async def test_automation_rate_no_other_outcomes(client):
    """With only definitive outcomes (no 'other'), automation_rate should be 1.0."""
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
async def test_automation_rate_with_other_outcome(client):
    """A single 'other' call (unresolved proxy) must lower automation_rate below 1."""
    from app.db.database import get_db
    from app.main import app

    async for db in app.dependency_overrides[get_db]():
        for rid, outcome in [("aut-a", "booked"), ("aut-b", "other")]:
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
async def test_seed_outcomes_are_valid_taxonomy(client):
    """Every seed call must use one of the 7 canonical outcome tags."""
    VALID_OUTCOMES = {
        "booked", "carrier_ineligible", "load_not_found",
        "equipment_mismatch", "negotiation_failed", "not_interested", "other",
    }
    await _seed(client)

    from app.db.database import get_db
    from app.main import app
    from sqlalchemy import select

    async for db in app.dependency_overrides[get_db]():
        rows = list((await db.execute(select(Call))).scalars().all())
        break

    for row in rows:
        assert row.outcome in VALID_OUTCOMES, (
            f"run_id={row.run_id!r} has off-taxonomy outcome {row.outcome!r}"
        )


@pytest.mark.asyncio
async def test_automation_rate_seeded_data(client):
    """automation_rate over seed = (non-other outcomes) / total; must be between 0 and 1."""
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    rate = data["capacity"]["automation_rate"]
    assert 0.0 <= rate <= 1.0
    # Seed has 1 'other' row out of 46 total -> 45/46 ~= 0.978
    assert rate == pytest.approx(45 / 46, rel=1e-4)


@pytest.mark.asyncio
async def test_sentiment_counts_sum_to_total(client):
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    overall = data["sentiment"]["overall"]
    total = data["capacity"]["calls_handled"]
    assert overall["positive"] + overall["neutral"] + overall["negative"] == total


@pytest.mark.asyncio
async def test_sentiment_booked_not_booked_split(client):
    """booked + not_booked sentiment counts sum to overall."""
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    sent = data["sentiment"]
    for key in ("positive", "neutral", "negative"):
        assert sent["booked"][key] + sent["not_booked"][key] == sent["overall"][key], (
            f"sentiment.{key}: booked+not_booked != overall"
        )
    # Booked calls should be present and have non-trivial positive sentiment
    assert sent["booked"]["positive"] > 0


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
    """Realized avg_pct_over_loadboard must not exceed the tier's ceiling_multiplier - 1.

    Realized margin need not be monotonic across tiers (posted-rate bookings
    pull individual tier averages down); the ceiling_multiplier is the design
    ceiling, not the realized outcome.
    """
    await _seed(client)
    resp = await client.get("/metrics", headers=VALID)
    data = resp.json()
    for t in data["margin"]["by_urgency_tier"]:
        cap = t["ceiling_multiplier"] - 1.0
        if t["loads"] > 0:
            assert t["avg_pct_over_loadboard"] <= cap + 1e-6, (
                f"{t['tier']}: realized {t['avg_pct_over_loadboard']:.4%} > ceiling {cap:.4%}"
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
