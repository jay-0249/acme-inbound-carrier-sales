# API Contract

Base URL (local dev): `http://localhost:8000`

All endpoints require an `X-API-Key` header. Two keys exist with different scopes:

| Key (env var) | Scope | Used by |
|---------------|-------|---------|
| `LOADS_API_KEY` | Full access — all endpoints | HappyRobot agent workflow config. Never sent to the browser. |
| `READ_API_KEY` | Read-only — GET endpoints only | Browser dashboard (`VITE_API_KEY`). Safe to bake into the bundle. |

**Read-only endpoints** (accept either key):
`GET /metrics`, `GET /loads`, `GET /loads/{id}`, `GET /verify-carrier/{mc_number}`

**Write endpoints** (accept `LOADS_API_KEY` only):
`POST /calls`, `POST /negotiate`

A read key sent to a write endpoint returns `401`. Missing or unrecognised key returns `401` on any endpoint.

**Fallback:** if `READ_API_KEY` is unset in the environment, read endpoints accept only `LOADS_API_KEY` (preserves local-dev behaviour without migration).

---

## Loads

### GET /loads

Returns all loads, optionally filtered.

**Query parameters** (all optional):

| Parameter | Type | Description |
|-----------|------|-------------|
| `equipment_type` | string | Exact match (e.g. `dry_van`, `reefer`, `flatbed`) |
| `origin` | string | Case-insensitive partial match on origin field |
| `destination` | string | Case-insensitive partial match on destination field |

**Response** `200 OK` — JSON array of load objects (may be empty):

```json
[
  {
    "load_id": "LD-001",
    "origin": "Chicago, IL",
    "destination": "Detroit, MI",
    "pickup_datetime": "2026-06-25T08:00:00",
    "delivery_datetime": "2026-06-25T16:00:00",
    "equipment_type": "dry_van",
    "loadboard_rate": 1250.0,
    "notes": "Dock appointment required.",
    "weight": 38000,
    "commodity_type": "Electronics",
    "num_of_pieces": 24,
    "miles": 281,
    "dimensions": "48x96x96 in"
  }
]
```

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | Success (empty array if no match) |
| `401` | Missing or invalid `X-API-Key` |

---

### GET /loads/{load_id}

Returns a single load by its identifier.

**Path parameter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `load_id` | string | Exact load identifier (e.g. `LD-001`) |

**Response** `200 OK` — single load object (same shape as array element above).

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | Load found |
| `401` | Missing or invalid `X-API-Key` |
| `404` | No load with that `load_id` |

---

---

## Carrier Verification

### GET /verify-carrier/{mc_number}

Checks whether a carrier is eligible to operate by querying the FMCSA QCMobile docket-number lookup. The voice agent calls this at the start of every inbound call.

**Path parameter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `mc_number` | string | Motor Carrier number supplied by the caller |

**Response** `200 OK`:

```json
{
  "mc_number": "123456",
  "eligible": true,
  "carrier_name": "ACME FREIGHT INC",
  "dot_number": "1234567"
}
```

`eligible` is `true` only when FMCSA returns `allowedToOperate == "Y"`. `carrier_name` prefers `legalName`, falls back to `dbaName`. Both `carrier_name` and `dot_number` are `null` when the MC number is not found.

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | FMCSA responded (eligible or not, including MC not found) |
| `401` | Missing or invalid `X-API-Key` |
| `502` | FMCSA request failed or timed out |

**Notes:**
- Safety-rating and insurance parsing are not included; add as future work once the FMCSA `dotNumber` enrichment call is wired in.
- A follow-up `GET /qc/services/carriers/{dotNumber}` would provide insurance and safety data if the docket response is thin (documented as future work in the carrier router).

---

---

## Calls

### POST /calls

Upserts a call record by `run_id`. Called by the HappyRobot post-call webhook after every session ends. Safe to call multiple times for the same `run_id`; only non-null fields in the request overwrite existing values.

**Request body** (`Content-Type: application/json`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `run_id` | string | Yes | HappyRobot `current.run_id` |
| `carrier_eligible` | boolean | No | Accepts `true`/`false` (bool or string). Set from the `/verify-carrier` result. |
| `outcome` | string | No | e.g. `booked`, `no_match`, `ineligible`, `price_gap`, `transferred` |
| `outcome_source` | string | No | `resolved` or `classified`. Defaults to `classified` when outcome is set and no source is given. A `resolved` outcome on an existing row cannot be overwritten by a later `classified` post. |
| `sentiment` | string | No | `positive`, `negative`, or `neutral` |
| `duration` | number | No | Call duration in seconds |
| `run_url` | string | No | HappyRobot run permalink |
| `mc_number` | string | No | Carrier MC number |
| `carrier_name` | string | No | Carrier legal name |
| `load_id` | string | No | Matched load ID |
| `final_rate` | number | No | Agreed rate in USD |

`load_found` is intentionally absent from the request body. Whether a load was found is captured by the outcome classifier via the `load_not_found` tag; setting it from `load_id` presence would be wrong because `load_id` is just the identifier the carrier mentioned, not confirmation that a matching load was returned.

**Response** `200 OK` — the upserted call row:

```json
{
  "run_id": "run-abc123",
  "mc_number": "288570",
  "carrier_name": "FEDEX GROUND PACKAGE SYSTEM CORPORATION",
  "carrier_eligible": null,
  "load_id": "LD-001",
  "load_found": null,
  "outcome": "booked",
  "outcome_source": "classified",
  "sentiment": "positive",
  "final_rate": 1300.0,
  "rounds": 2,
  "duration": 180.0,
  "run_url": null,
  "created_at": "2026-06-26T10:00:00",
  "updated_at": "2026-06-26T10:01:00"
}
```

`rounds` is always recomputed as the count of `negotiation_events` rows for this `run_id`.

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | Row created or updated |
| `401` | Missing or invalid `X-API-Key` |
| `422` | `run_id` missing from request body |

---

## Database Tables

### calls

| Column | Type | Notes |
|--------|------|-------|
| `run_id` | text PK | HappyRobot run identifier |
| `mc_number` | text | nullable |
| `carrier_name` | text | nullable |
| `carrier_eligible` | boolean | nullable; set by earlier tool calls |
| `load_id` | text | nullable |
| `load_found` | boolean | nullable; set by earlier tool calls |
| `outcome` | text | nullable |
| `outcome_source` | text | nullable; `resolved` or `classified` |
| `sentiment` | text | nullable |
| `final_rate` | numeric | nullable |
| `rounds` | int | nullable; recomputed from `negotiation_events` on every upsert |
| `duration` | numeric | nullable; seconds |
| `run_url` | text | nullable |
| `created_at` | timestamp | set on insert |
| `updated_at` | timestamp | updated on every upsert |

### negotiation_events

| Column | Type | Notes |
|--------|------|-------|
| `id` | int PK | autoincrement |
| `run_id` | text (indexed) | no FK constraint; events may arrive before the calls row exists |
| `round` | int | negotiation round number |
| `load_id` | text | load being negotiated |
| `carrier_offer` | numeric | carrier's offer in USD |
| `agent_price` | numeric | agent's counter or accepted price |
| `decision` | text | `accept`, `counter`, or `final` |
| `created_at` | timestamp | set on insert |

---

## Negotiate

### POST /negotiate

Runs one round of deterministic price negotiation. The server owns all pricing math and the round counter. The agent passes only what it heard from the carrier; it never computes a price or supplies a round number.

**Request body:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `run_id` | string | Yes | HappyRobot `current.run_id` |
| `load_id` | string | Yes | Load being negotiated; 404 if not found |
| `carrier_offer` | number | Yes | Dollar amount the carrier just stated; must be > 0 |

**Response** `200 OK`:

```json
{
  "run_id": "run-abc123",
  "round": 1,
  "decision": "counter",
  "agent_price": 1300.0,
  "ceiling": 1350.0,
  "negotiation_status": "negotiating"
}
```

| Field | Notes |
|-------|-------|
| `round` | Server-derived from `COUNT(negotiation_events WHERE run_id)` + 1 |
| `decision` | `accept` — carrier offer accepted at carrier's price; `counter` — broker counters at `agent_price`; `final` — ceiling reached, take it or leave it |
| `agent_price` | The dollar figure the agent reads to the carrier |
| `ceiling` | Urgency-scaled ceiling, exposed for observability |
| `negotiation_status` | `ceiling_reached` when `decision == "final"`, else `negotiating` |

**Urgency ceiling tiers** (computed from days until `pickup_datetime`):

| Days to pickup | Multiplier | Example (rate $1,250) |
|----------------|------------|----------------------|
| <= 2 (incl. today / past) | 1.08 | ceiling $1,350 |
| 3-5 | 1.06 | ceiling $1,325 |
| > 5 | 1.04 | ceiling $1,300 |

**Front-loaded ladder** (steps rounded to nearest $25, clamped to ceiling):

| Round | Step formula |
|-------|-------------|
| 1 | `loadboard_rate + 0.60 * band` |
| 2 | `loadboard_rate + 0.85 * band` |
| >= 3 | `ceiling` |

where `band = ceiling - loadboard_rate`.

**Decision logic:**
- `carrier_offer <= step` -> `accept` at `carrier_offer` (never pay more than asked)
- `round < 3` and offer above step -> `counter` at `step`
- `round >= 3` and offer still above ceiling -> `final` at `ceiling`
- Guardrail: `agent_price = min(agent_price, ceiling)` for `counter` and `final`, independent of ladder math.

**On accept:** upserts `calls.final_rate = agent_price` and sets `calls.load_id` if not already set. Creates the `calls` row if absent (webhook fires after `/negotiate`). Does not touch `outcome`, `outcome_source`, `sentiment`, or `rounds`.

**On non-accept:** `final_rate` is never written. A carrier who walks away leaves `final_rate` null.

Each invocation writes exactly one `negotiation_events` row and advances the round counter by one.

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | Negotiation round completed |
| `401` | Missing or invalid `X-API-Key` |
| `404` | `load_id` not found |
| `422` | Missing required field or `carrier_offer <= 0` |

---

## Metrics

### GET /metrics

Returns all broker dashboard aggregates in a single payload. Computed from
the `calls`, `negotiation_events`, and `loads` tables. No filters; no
time-series. The frontend makes one call and renders all panels.

**Response** `200 OK`:

```json
{
  "capacity": {
    "calls_handled": 46,
    "calls_after_hours": 10,
    "calls_missed": 0,
    "booking_rate": 0.608695,
    "loads_booked": 28,
    "automation_rate": 0.978260
  },
  "value_model": {
    "rep_hours_freed": 2.34,
    "assumed_loaded_wage_per_hour": 48,
    "assumed_agent_cost_per_call": 0.75,
    "value_captured_usd": 78.18
  },
  "margin": {
    "avg_pct_over_loadboard": 0.018500,
    "total_dollars_over_loadboard": 1240.00,
    "by_urgency_tier": [
      {"tier": "<=2 days (8%)", "avg_pct_over_loadboard": 0.022, "ceiling_multiplier": 1.08, "loads": 9},
      {"tier": "3-5 days (6%)", "avg_pct_over_loadboard": 0.007, "ceiling_multiplier": 1.06, "loads": 6},
      {"tier": ">5 days (4%)",  "avg_pct_over_loadboard": 0.015, "ceiling_multiplier": 1.04, "loads": 10}
    ]
  },
  "outcomes": [
    {"outcome": "booked",              "count": 28, "pct": 0.608695},
    {"outcome": "negotiation_failed",  "count": 6,  "pct": 0.130434},
    {"outcome": "carrier_ineligible",  "count": 3,  "pct": 0.065217},
    {"outcome": "load_not_found",      "count": 3,  "pct": 0.065217},
    {"outcome": "not_interested",      "count": 3,  "pct": 0.065217},
    {"outcome": "equipment_mismatch",  "count": 2,  "pct": 0.043478},
    {"outcome": "transferred_to_human","count": 1,  "pct": 0.021739}
  ],
  "top_decline_reason": {"outcome": "negotiation_failed", "count": 6},
  "sentiment": {"positive": 25, "neutral": 14, "negative": 7},
  "negotiation": {
    "avg_rounds_to_close": 1.71,
    "settled_distribution": {
      "round_1": 8, "round_2": 9, "round_3": 3, "walked": 6
    }
  },
  "recent_calls": [
    {
      "run_id": "seed-001",
      "carrier_name": "ACME FREIGHT LLC",
      "load_id": "LD-001",
      "outcome": "booked",
      "sentiment": "positive",
      "final_rate": 1275.0,
      "loadboard_rate": 1250.0,
      "pct_over_loadboard": 0.02,
      "rounds": 2,
      "created_at": "2026-06-26T14:22:00",
      "run_url": null
    }
  ]
}
```

**Field notes:**

| Field | Description |
|-------|-------------|
| `capacity.calls_missed` | Always 0. The agent answers every inbound call; there is no missed-call signal in the current HappyRobot integration. Documented as a measured stance, not a gap. |
| `capacity.calls_after_hours` | `created_at` before 8am or at/after 6pm UTC, or on a Saturday/Sunday. |
| `capacity.automation_rate` | Share of calls the agent resolved to a definitive outcome (all taxonomy tags except `other`), divided by total. `other` is the proxy for calls the agent could not cleanly resolve; the POC has no live human-transfer wired, so every non-`other` outcome represents an agent-handled call. |
| `value_model.*` | Explicitly modeled estimates. `assumed_loaded_wage_per_hour` ($48) and `assumed_agent_cost_per_call` ($0.75) are stated assumptions; all other figures are measured from the DB. The UI must display these as estimates with stated assumptions. |
| `margin.by_urgency_tier` | Each entry has `avg_pct_over_loadboard` (realized, measured), `ceiling_multiplier` (designed ceiling: 1.08/1.06/1.04), and `loads` (booked count). Realized margin need not descend monotonically — posted-rate bookings pull tier averages down independently of urgency. The UI should display realized margin vs. ceiling per tier, not imply the realized values follow the ceiling pattern. Tier boundaries use the same `(pickup_date - today).days` formula as `/negotiate`. |
| `margin.avg_pct_over_loadboard` | Mean over booked calls with a known load and final_rate. 0..1 float (multiply by 100 for %). |
| `outcomes` | Ranked descending by count. `pct` sums to 1.0 over all entries. |
| `top_decline_reason` | Largest non-booked outcome. |
| `negotiation.avg_rounds_to_close` | Average over booked-via-negotiation calls only (where the last event is `accept`). |
| `negotiation.settled_distribution.walked` | Count of run_ids whose last event decision is `final` (ceiling hit, carrier walked). |
| `recent_calls` | Newest first, capped at 25. `pct_over_loadboard` is null if load or final_rate is unknown. |

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | Success |
| `401` | Missing or invalid `X-API-Key` |
