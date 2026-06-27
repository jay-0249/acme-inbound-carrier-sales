# Design Decisions

Entries are appended as tasks are completed. Each line: decision, then why.

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
- **Seed pickup dates computed relative to today at import time** - hardcoded 2026 dates would all fall into the <=2-day urgency tier the day after deployment; relative offsets keep all three tiers live for any demo date.

## Task 3 - Call records and POST /calls

- **carrier_eligible accepts bool or string in CallCreate** - HappyRobot passes extracted values as strings; tolerant coercion ("true"/"True"/true -> True, "false"/"False"/false -> False, anything else -> None) means the endpoint works regardless of how the platform serializes the field.
- **load_found excluded from CallCreate** - whether a load was found is captured by the outcome classifier's `load_not_found` tag; a load_id being present does not imply the load was found (it is the carrier's stated reference, not a confirmed match).

## Task 2 - FMCSA carrier verification endpoint

- **HTTP 200 for MC-not-found** - the voice agent has a single branch for "not eligible"; a 404 would require a second status-code check for the same outcome.
- **HTTP 502 for FMCSA failures** - propagates upstream unavailability without leaking internal detail; the agent treats it as a hard stop and transfers to human.
- **5-second timeout on FMCSA call** - keeps call latency bounded; FMCSA QCMobile is occasionally slow and a hung request would stall the voice session.
- **`legalName` preferred over `dbaName`** - legal name is the authoritative carrier identity; DBA is a fallback for carriers that only register a trade name.
- **`unittest.mock` for httpx, no extra test dependencies** - `respx` would be cleaner but adds a dependency; `AsyncMock` over `httpx.AsyncClient` is sufficient for the three required cases.
