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

## Task 2 - FMCSA carrier verification endpoint

- **HTTP 200 for MC-not-found** - the voice agent has a single branch for "not eligible"; a 404 would require a second status-code check for the same outcome.
- **HTTP 502 for FMCSA failures** - propagates upstream unavailability without leaking internal detail; the agent treats it as a hard stop and transfers to human.
- **5-second timeout on FMCSA call** - keeps call latency bounded; FMCSA QCMobile is occasionally slow and a hung request would stall the voice session.
- **`legalName` preferred over `dbaName`** - legal name is the authoritative carrier identity; DBA is a fallback for carriers that only register a trade name.
- **`unittest.mock` for httpx, no extra test dependencies** - `respx` would be cleaner but adds a dependency; `AsyncMock` over `httpx.AsyncClient` is sufficient for the three required cases.
