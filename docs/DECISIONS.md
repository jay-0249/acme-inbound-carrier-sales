# Design Decisions

Entries are appended as tasks are completed. Each line: decision, then why.

---

## Assumptions

### One load per call

The `calls` table is one row per call, keyed by `run_id`, with single-valued columns (`load_id`, `final_rate`, `outcome`). This deliberately assumes a single load is negotiated per call, which matches the dominant real-world inbound pattern: a carrier calls about a specific load they saw posted and references its `load_id`.

- `negotiation_events` is keyed by `run_id` AND `load_id`, so per-load negotiation history and round counts are correct even if more than one load is touched in a call (each load gets its own independent round budget; counts never bleed across loads).
- The `calls` row, however, holds only ONE `load_id` / `final_rate` / `outcome`. If multiple loads are discussed in a single call, the call-level summary reflects only the most recently handled load.

This is an accepted limitation for the POC, not a bug. Supporting multiple loads per call as first-class call records would require keying call-level outcomes by `run_id` + `load_id` (a "call" becoming a parent of one or more "load engagements") and aggregating the dashboard at that grain. Documented as future work.

---

## Task 1 - Loads API slice

- **Async SQLAlchemy with aiosqlite** - matches FastAPI's async model; keeps the pattern consistent for later endpoints that will do more I/O.
- **Lazy engine initialization** (`_init_engine` called on first `get_db` invocation) - lets tests set `DATABASE_URL` via env before any connection is created, without needing dependency overrides for the engine itself.
- **`@lru_cache` on `get_settings()`** - prevents re-reading the env on every request while still being overridable via FastAPI `dependency_overrides` in tests.
- **`verify_api_key` takes `Settings` via `Depends`** - makes the API key injectable in tests; avoids reading the module-level singleton in production and the override in tests without patching globals.
- **`TESTING=1` env var skips lifespan DB setup** - lets tests provide their own isolated engine and seed without fighting the startup hooks; no test-only code paths in production.
- **Seed is idempotent (skip if table non-empty)** - safe to call on every startup restart; no duplicate-key errors if the DB already has data.
- **Origin/destination filters use `ilike` partial match** - voice agents will say "Chicago" not "Chicago, IL"; substring match is more useful than exact match for free-text location fields.
- **Equipment type filter is exact match** - equipment type is a controlled vocabulary (`dry_van`, `reefer`, `flatbed`); partial match would silently return wrong results.
- **Seed data spread across all three urgency tiers** - ensures the negotiation ceiling logic (1.05/1.10/1.15) is visibly exercisable in the demo with different loads.
- **HAZMAT and oversize loads included in seed** - tests the matching gate's notes-checking path in a later task and makes the demo more realistic.
- **SQLite `check_same_thread` not needed** - using async sessions; aiosqlite handles thread safety internally.
- **`tmp_path` fixture for test DB** - each test function gets an isolated file-backed SQLite; avoids shared-memory URI complexity and connection pool conflicts between the test setup code and the ASGI app.

## Task 3 - Call records and POST /calls

- **run_id-keyed upsert, not INSERT** - HappyRobot may call the webhook more than once for the same run; idempotent upsert means duplicate posts are safe and future tool calls can pre-create the row before the webhook fires.
- **"resolved" outcome wins over "classified"** - the deterministic /resolve endpoint is the authoritative source of truth; the LLM classifier's label must never silently overwrite a human-verified outcome.
- **No FK from negotiation_events to calls** - negotiation events are written mid-call before the webhook fires; a hard FK would either block those writes or require the calls row to exist first, coupling two independent write paths.
- **rounds always recomputed, not stored incrementally** - counting from negotiation_events on every upsert is O(n) but n is at most 3; avoids drift between the stored counter and the actual event log.
- **outcome_source defaults to "classified" on insert** - makes the source field non-null whenever outcome is set, so the dashboard can always filter by source without null-checks.
## Task 4 - POST /negotiate and relative-date seed

- **Front-loaded ladder (60/85/100% of band)** - biggest counter first to close fast; tapering to ceiling avoids giving away the room on round 1 while preserving a credible final offer.
- **Server-owned round count from negotiation_events** - the agent never supplies a round number; `COUNT(events WHERE run_id) + 1` is the only source of truth, making hallucinated counts impossible.
- **Absolute ceiling clamp as independent safety net** - `min(agent_price, ceiling)` is applied after all ladder and rounding math; it holds even if the ladder formula is later changed or broken.
- **Accept price is exact carrier_offer, not rounded** - rounding an accepted price up would mean paying more than the carrier asked; rounding down is bad faith; keeping it exact is the only defensible choice.
- **/negotiate upserts calls.final_rate only on accept** - a counter or final that never closes leaves final_rate null, which correctly signals "no deal" to the dashboard.
- **final_rate resolution order in POST /calls: accept-event price > loadboard_rate for booked > null** - if /negotiate fired and the carrier accepted, that price is already on the row and is left untouched; if the carrier booked at the posted rate without negotiating, loadboard_rate is the only defensible figure; any other outcome leaves final_rate null. The agent's last counter offer is never used -- a carrier can reject every counter and then accept the posted rate, making the last offer wrong.
- **Seed pickup dates computed relative to today at import time** - hardcoded 2026 dates would all fall into the <=2-day urgency tier the day after deployment; relative offsets keep all three tiers live for any demo date.

## Task 3 - Call records and POST /calls

- **carrier_eligible accepts bool or string in CallCreate** - HappyRobot passes extracted values as strings; tolerant coercion ("true"/"True"/true -> True, "false"/"False"/false -> False, anything else -> None) means the endpoint works regardless of how the platform serializes the field.
- **load_found excluded from CallCreate** - whether a load was found is captured by the outcome classifier's `load_not_found` tag; a load_id being present does not imply the load was found (it is the carrier's stated reference, not a confirmed match).

## Task 5 - GET /metrics and synthetic call-history seed

**Design summary.** The metrics endpoint is a single-query aggregation layer over
the `calls`, `negotiation_events`, and `loads` tables. It returns one JSON payload
covering capacity, margin, outcomes, sentiment, and negotiation depth. The frontend
makes one call and renders all panels. No time-series, no filters, no sub-endpoints:
this matches the demo scope and avoids premature surface area.

- **Single GET /metrics payload** - the dashboard makes one round-trip; all panels
  share the same snapshot timestamp; no waterfall of panel-level requests.
- **value_model is explicitly a transparent estimate** - `rep_hours_freed * $48/hr -
  calls * $0.75` is defensible as a first-order broker ROI model. The $48 loaded wage
  and $0.75 agent cost are stated assumptions in both the response payload and the UI.
  Every other metric is measured directly from the DB. Never label any value_model
  figure as "savings" without the assumption caveat visible.
- **calls_missed is always 0** - the agent answers every inbound call; there is no
  missed-call signal from HappyRobot in the current integration. Returning 0 with a
  documented stance is more honest than omitting the metric or fabricating a proxy.
- **after_hours uses UTC proxy** - `created_at` is stored as naive UTC; treating it
  as local time is a known approximation. For a POC demo all traffic is domestic US,
  so the error is bounded. A future fix would store timezone alongside the timestamp.
- **urgency tier in /metrics uses pickup_datetime from the joined load** - same
  `(pickup_date - today).days` formula as /negotiate so tier assignments are
  consistent across the system.
- **margin.by_urgency_tier shows REALIZED margin alongside the designed ceiling** - each
  tier entry returns both `avg_pct_over_loadboard` (measured) and `ceiling_multiplier`
  (the 1.08/1.06/1.04 design ceiling). Realized margin need not descend monotonically
  across tiers: a carrier who accepts the posted rate contributes 0% over loadboard
  regardless of urgency tier, and posted-rate bookings are distributed unevenly across
  tiers in both real and seed data. The 8/6/4% pattern is the ceiling for what we CAN
  pay, not a guarantee of what we DO pay. The seed is NOT rearranged to force a clean
  descent — that would be reverse-engineering data to produce a prettier chart. The UI
  should frame this as "realized margin vs. ceiling by tier" so the asymmetry is honest.
- **automation_rate = (non-"other" outcomes) / total** - the outcome taxonomy has no
  explicit "transferred to human" tag, and the POC has no live human-transfer wired.
  `other` is the catch-all for calls the agent could not cleanly resolve or classify,
  making it the closest honest proxy for "needed a human / fell through". Every other
  tag (booked, the specific declines, ineligible, not_found, mismatch) represents a
  clear terminal outcome the agent reached on its own. This definition is explainable
  on a whiteboard without inventing a new tag or stretching the taxonomy.
- **Synthetic seed prefixed "seed-"** - all 46 synthetic call rows have `run_id`
  starting with `seed-`. This lets `seed_calls()` use a single `SELECT ... LIKE 'seed-%'`
  idempotency check (skip if any seed row exists), and keeps real test calls
  unambiguously separate. To reseed: delete the DB and restart.
- **Synthetic created_at spread across 14 days, ~22% after-hours** - timestamps are
  computed relative to `date.today()` at seed time using `date.today() - timedelta(days=N)`.
  Never hardcoded. After-hours rows use hours before 8 or at/after 19 (or weekend),
  giving the "after-hours coverage" dashboard metric real texture without fabricating
  a separate signal.
- **Negotiation events for seed rows follow the ladder math** - intermediate events
  use the 60%/85% band steps from `services/negotiation.py`; the final event is
  `accept` (booked) or `final` (walked). This means the `settled_distribution` and
  `avg_rounds_to_close` metrics are grounded in the same logic the live agent uses.

## API key scoping — read key vs. full key

The dashboard's API key (`VITE_API_KEY`) is baked into the browser bundle at build time and is therefore public — anyone who opens DevTools can read it. Giving the browser the full `LOADS_API_KEY` would mean a public key can write call records and drive negotiation rounds, which is an unnecessary blast radius.

**Decision:** split into two keys. `LOADS_API_KEY` (full access) is used only by the HappyRobot agent in its workflow config, which is server-side and never reaches the browser. `READ_API_KEY` is a separate credential accepted only on the four GET endpoints the dashboard needs. A read key on a write endpoint returns 401.

**Implementation:** `verify_read_access` dependency in `security.py` accepts either key; `verify_api_key` (full) remains on write endpoints. `LOADS_API_KEY` is the superset — it works everywhere, so the agent needs only one key. If `READ_API_KEY` is unset (local dev, existing deployments), read endpoints fall back to accepting `LOADS_API_KEY` only, preserving backward compatibility without a migration step.

**Why not scopes/JWTs:** this is a demo POC with two actors (agent and dashboard) and two operations (write and read). Two static keys is the simplest defensible design; adding a token system would be scope creep with no additional protection for the actual threat (browser key exposure).

---

## Task 2 - FMCSA carrier verification endpoint

- **HTTP 200 for MC-not-found** - the voice agent has a single branch for "not eligible"; a 404 would require a second status-code check for the same outcome.
- **HTTP 502 for FMCSA failures** - propagates upstream unavailability without leaking internal detail; the agent treats it as a hard stop and transfers to human.
- **5-second timeout on FMCSA call** - keeps call latency bounded; FMCSA QCMobile is occasionally slow and a hung request would stall the voice session.
- **`legalName` preferred over `dbaName`** - legal name is the authoritative carrier identity; DBA is a fallback for carriers that only register a trade name.
- **`unittest.mock` for httpx, no extra test dependencies** - `respx` would be cleaner but adds a dependency; `AsyncMock` over `httpx.AsyncClient` is sufficient for the three required cases.
