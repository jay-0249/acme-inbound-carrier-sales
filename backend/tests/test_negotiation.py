"""
Negotiation tests — two layers:
  1. Service unit tests (pure functions, no DB, no async).
  2. API integration tests (full endpoint via ASGI client).

Seed load used throughout (from conftest):
  LD-001: pickup today+0, loadboard_rate=1250, 8% tier
    ceiling  = 1250 * 1.08 = 1350   (exact $25 multiple)
    band     = 100
    step r1  = round25(1250 + 60)  = round25(1310) = 1300
    step r2  = round25(1250 + 85)  = round25(1335) = 1325
    step r3+ = min(round25(1350), 1350)             = 1350
"""
from datetime import date, timedelta

import pytest

from app.services.negotiation import compute_ceiling, negotiate

VALID = {"X-API-Key": "test-api-key-abc123"}


# ─── SERVICE UNIT TESTS ───────────────────────────────────────────────────────

def test_ceiling_tier_urgent():
    assert compute_ceiling(1000, 0) == pytest.approx(1080)
    assert compute_ceiling(1000, 2) == pytest.approx(1080)
    assert compute_ceiling(1000, -1) == pytest.approx(1080)  # past pickup = most urgent


def test_ceiling_tier_moderate():
    assert compute_ceiling(1000, 3) == pytest.approx(1060)
    assert compute_ceiling(1000, 5) == pytest.approx(1060)


def test_ceiling_tier_low():
    assert compute_ceiling(1000, 6) == pytest.approx(1040)
    assert compute_ceiling(1000, 20) == pytest.approx(1040)


def _neg(carrier_offer: float, round_num: int, pickup_days: int = 0, rate: float = 1250.0):
    """Run negotiate() with today-relative pickup and controlled inputs."""
    return negotiate(
        carrier_offer=carrier_offer,
        loadboard_rate=rate,
        pickup_date=date.today() + timedelta(days=pickup_days),
        round_num=round_num,
    )


def test_round1_high_offer_returns_counter():
    # 1400 > step1(1300) -> counter at 1300
    r = _neg(carrier_offer=1400, round_num=1)
    assert r.decision == "counter"
    assert r.agent_price == 1300
    assert r.negotiation_status == "negotiating"


def test_round1_low_offer_returns_accept():
    # 1280 <= step1(1300) -> accept at exact offer
    r = _neg(carrier_offer=1280, round_num=1)
    assert r.decision == "accept"
    assert r.agent_price == 1280


def test_accept_price_equals_carrier_offer_not_rounded():
    # carrier_offer=1287 is below step1(1300); accepted at exactly 1287, not rounded
    r = _neg(carrier_offer=1287, round_num=1)
    assert r.decision == "accept"
    assert r.agent_price == 1287
    assert r.agent_price <= 1287  # invariant: never pay more than asked


def test_three_rounds_stubborn_offer():
    # 1400 > every step; rounds 1,2 -> counter; round 3 -> final
    r1 = _neg(carrier_offer=1400, round_num=1)
    assert r1.decision == "counter" and r1.agent_price == 1300

    r2 = _neg(carrier_offer=1400, round_num=2)
    assert r2.decision == "counter" and r2.agent_price == 1325

    r3 = _neg(carrier_offer=1400, round_num=3)
    assert r3.decision == "final"
    assert r3.agent_price == 1350
    assert r3.negotiation_status == "ceiling_reached"


def test_agent_price_never_exceeds_ceiling_any_round():
    # rate=1000, today+10 (>5 days): ceiling=1040. Absurd offer to stress the clamp.
    for round_num in [1, 2, 3, 4, 5]:
        r = negotiate(
            carrier_offer=5000,
            loadboard_rate=1000,
            pickup_date=date.today() + timedelta(days=10),
            round_num=round_num,
        )
        assert r.agent_price <= r.ceiling, (
            f"round {round_num}: agent_price {r.agent_price} > ceiling {r.ceiling}"
        )


def test_guardrail_clamp_explicit():
    # rate=1000, >5 days -> ceiling=1040 (NOT a $25 multiple).
    # round3 raw step = ceiling = 1040; round25(1040) = 1050 > 1040.
    # Without the clamp agent_price would be 1050. With it: 1040.
    r = negotiate(
        carrier_offer=5000,
        loadboard_rate=1000,
        pickup_date=date.today() + timedelta(days=10),
        round_num=3,
    )
    assert r.decision == "final"
    assert r.ceiling == pytest.approx(1040)
    assert r.agent_price == pytest.approx(1040)  # clamp held; 1050 would violate it


def test_counter_and_final_prices_are_25_multiples():
    # LD-001 equivalent: ceiling=1350 (exact $25 multiple) -> all steps clean
    for round_num, expected in [(1, 1300), (2, 1325), (3, 1350)]:
        r = _neg(carrier_offer=5000, round_num=round_num)
        assert r.agent_price == expected
        assert r.agent_price % 25 == 0, (
            f"round {round_num}: agent_price {r.agent_price} not a $25 multiple"
        )


# ─── API INTEGRATION TESTS ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_counter_writes_event_and_returns_correct_fields(client):
    resp = await client.post(
        "/negotiate",
        json={"run_id": "neg-001", "load_id": "LD-001", "carrier_offer": 1400},
        headers=VALID,
    )
    assert resp.status_code == 200
    d = resp.json()
    assert d["run_id"] == "neg-001"
    assert d["round"] == 1
    assert d["decision"] == "counter"
    assert d["agent_price"] == 1300
    assert d["ceiling"] == pytest.approx(1350)
    assert d["negotiation_status"] == "negotiating"


@pytest.mark.asyncio
async def test_round_is_server_derived(client):
    # Two calls to the same run_id must return rounds 1 and 2 respectively.
    r1 = await client.post(
        "/negotiate",
        json={"run_id": "neg-002", "load_id": "LD-001", "carrier_offer": 1400},
        headers=VALID,
    )
    assert r1.json()["round"] == 1
    r2 = await client.post(
        "/negotiate",
        json={"run_id": "neg-002", "load_id": "LD-001", "carrier_offer": 1400},
        headers=VALID,
    )
    assert r2.json()["round"] == 2


@pytest.mark.asyncio
async def test_accept_sets_calls_final_rate_and_load_id(client):
    # 1250 == loadboard_rate; step1 = 1300; 1250 <= 1300 -> accept at 1250
    resp = await client.post(
        "/negotiate",
        json={"run_id": "neg-003", "load_id": "LD-001", "carrier_offer": 1250},
        headers=VALID,
    )
    assert resp.json()["decision"] == "accept"
    assert resp.json()["agent_price"] == 1250

    calls = await client.post("/calls", json={"run_id": "neg-003"}, headers=VALID)
    assert calls.json()["final_rate"] == 1250
    assert calls.json()["load_id"] == "LD-001"


@pytest.mark.asyncio
async def test_accept_price_never_exceeds_carrier_offer(client):
    resp = await client.post(
        "/negotiate",
        json={"run_id": "neg-004", "load_id": "LD-001", "carrier_offer": 1287},
        headers=VALID,
    )
    d = resp.json()
    assert d["decision"] == "accept"
    assert d["agent_price"] <= 1287


@pytest.mark.asyncio
async def test_three_sequential_rounds_then_accept_at_ceiling(client):
    run = "neg-005"
    # Rounds 1-3: stubborn offer above ceiling
    for expected_round in [1, 2, 3]:
        r = await client.post(
            "/negotiate",
            json={"run_id": run, "load_id": "LD-001", "carrier_offer": 1400},
            headers=VALID,
        )
        assert r.json()["round"] == expected_round
    assert r.json()["decision"] == "final"
    assert r.json()["agent_price"] == 1350
    assert r.json()["negotiation_status"] == "ceiling_reached"

    # Round 4: carrier meets the ceiling -> accept
    r4 = await client.post(
        "/negotiate",
        json={"run_id": run, "load_id": "LD-001", "carrier_offer": 1350},
        headers=VALID,
    )
    assert r4.json()["round"] == 4
    assert r4.json()["decision"] == "accept"
    assert r4.json()["agent_price"] == 1350

    calls = await client.post("/calls", json={"run_id": run}, headers=VALID)
    assert calls.json()["final_rate"] == 1350


@pytest.mark.asyncio
async def test_non_accept_leaves_final_rate_null(client):
    await client.post(
        "/negotiate",
        json={"run_id": "neg-006", "load_id": "LD-001", "carrier_offer": 1400},
        headers=VALID,
    )
    calls = await client.post("/calls", json={"run_id": "neg-006"}, headers=VALID)
    assert calls.json()["final_rate"] is None


@pytest.mark.asyncio
async def test_accept_does_not_overwrite_outcome_or_sentiment(client):
    # Pre-create a calls row with outcome and sentiment
    await client.post(
        "/calls",
        json={
            "run_id": "neg-007",
            "outcome": "booked",
            "outcome_source": "resolved",
            "sentiment": "positive",
        },
        headers=VALID,
    )
    # Accept on the same run_id should only touch final_rate
    # 1250 == loadboard_rate -> accept (not sub-loadboard)
    await client.post(
        "/negotiate",
        json={"run_id": "neg-007", "load_id": "LD-001", "carrier_offer": 1250},
        headers=VALID,
    )
    calls = await client.post("/calls", json={"run_id": "neg-007"}, headers=VALID)
    assert calls.json()["outcome"] == "booked"
    assert calls.json()["outcome_source"] == "resolved"
    assert calls.json()["sentiment"] == "positive"
    assert calls.json()["final_rate"] == 1250


@pytest.mark.asyncio
async def test_unknown_load_returns_404(client):
    resp = await client.post(
        "/negotiate",
        json={"run_id": "neg-008", "load_id": "LD-FAKE", "carrier_offer": 1000},
        headers=VALID,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(client):
    resp = await client.post(
        "/negotiate",
        json={"run_id": "neg-009", "load_id": "LD-001", "carrier_offer": 1000},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_api_key_returns_401(client):
    resp = await client.post(
        "/negotiate",
        json={"run_id": "neg-009", "load_id": "LD-001", "carrier_offer": 1000},
        headers={"X-API-Key": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_zero_carrier_offer_returns_422(client):
    resp = await client.post(
        "/negotiate",
        json={"run_id": "neg-010", "load_id": "LD-001", "carrier_offer": 0},
        headers=VALID,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_negative_carrier_offer_returns_422(client):
    resp = await client.post(
        "/negotiate",
        json={"run_id": "neg-011", "load_id": "LD-001", "carrier_offer": -100},
        headers=VALID,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_urgency_ceiling_tiers_in_response(client):
    # LD-001 (today+0): 8% -> ceiling = 1250 * 1.08 = 1350
    r = await client.post(
        "/negotiate",
        json={"run_id": "tier-001", "load_id": "LD-001", "carrier_offer": 9999},
        headers=VALID,
    )
    assert r.json()["ceiling"] == pytest.approx(1350)

    # LD-008 (today+3): 6% -> ceiling = 2400 * 1.06 = 2544
    r = await client.post(
        "/negotiate",
        json={"run_id": "tier-002", "load_id": "LD-008", "carrier_offer": 9999},
        headers=VALID,
    )
    assert r.json()["ceiling"] == pytest.approx(2544)

    # LD-007 (today+11): 4% -> ceiling = 1650 * 1.04 = 1716
    r = await client.post(
        "/negotiate",
        json={"run_id": "tier-003", "load_id": "LD-007", "carrier_offer": 9999},
        headers=VALID,
    )
    assert r.json()["ceiling"] == pytest.approx(1716)


# ─── CONFIRM_OFFER — sub-loadboard floor ─────────────────────────────────────

# LD-001 loadboard_rate = 1250; anything < 1250 triggers confirm_offer.

def test_sub_loadboard_offer_returns_confirm_offer_service():
    """Service unit test: carrier_offer < loadboard_rate -> confirm_offer, no price."""
    r = _neg(carrier_offer=400, round_num=1)
    assert r.decision == "confirm_offer"
    assert r.agent_price is None
    assert r.negotiation_status == "needs_confirmation"
    assert r.message is not None and len(r.message) > 0
    assert "400" in r.message
    assert "1,250" in r.message  # loadboard_rate present in message


def test_at_loadboard_rate_goes_through_normal_path():
    """carrier_offer == loadboard_rate is NOT sub-loadboard; accept/counter/final as usual."""
    r = _neg(carrier_offer=1250, round_num=1)
    # 1250 == loadboard_rate; step1 = 1300; 1250 <= 1300 -> accept
    assert r.decision == "accept"
    assert r.agent_price == 1250


@pytest.mark.asyncio
async def test_confirm_offer_writes_no_event_row(client):
    """A confirm_offer must not write a negotiation_events row."""
    run = "confirm-001"
    resp = await client.post(
        "/negotiate",
        json={"run_id": run, "load_id": "LD-001", "carrier_offer": 400},
        headers=VALID,
    )
    assert resp.status_code == 200
    d = resp.json()
    assert d["decision"] == "confirm_offer"
    assert d["agent_price"] is None
    assert d["negotiation_status"] == "needs_confirmation"
    assert d["message"] is not None

    # Fetch calls row — must NOT have final_rate set
    calls = await client.post("/calls", json={"run_id": run}, headers=VALID)
    assert calls.json()["final_rate"] is None


@pytest.mark.asyncio
async def test_confirm_offer_does_not_consume_a_round(client):
    """Round counter is unchanged after a confirm_offer; next valid offer is still round 1."""
    run = "confirm-002"

    # Mis-transcription: sub-loadboard offer
    r_bad = await client.post(
        "/negotiate",
        json={"run_id": run, "load_id": "LD-001", "carrier_offer": 400},
        headers=VALID,
    )
    assert r_bad.json()["decision"] == "confirm_offer"
    assert r_bad.json()["round"] == 1  # what round WOULD be; counter not advanced

    # Corrected offer: now proceeds as round 1
    r_good = await client.post(
        "/negotiate",
        json={"run_id": run, "load_id": "LD-001", "carrier_offer": 1400},
        headers=VALID,
    )
    assert r_good.json()["round"] == 1
    assert r_good.json()["decision"] == "counter"


@pytest.mark.asyncio
async def test_confirm_offer_sets_no_final_rate(client):
    """confirm_offer must never write final_rate, even if called multiple times."""
    run = "confirm-003"
    for _ in range(2):
        await client.post(
            "/negotiate",
            json={"run_id": run, "load_id": "LD-001", "carrier_offer": 1},
            headers=VALID,
        )
    calls = await client.post("/calls", json={"run_id": run}, headers=VALID)
    assert calls.json()["final_rate"] is None
    # And the round counter is still 1 (no events written)
    r = await client.post(
        "/negotiate",
        json={"run_id": run, "load_id": "LD-001", "carrier_offer": 1400},
        headers=VALID,
    )
    assert r.json()["round"] == 1
