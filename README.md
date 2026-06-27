# Acme Inbound Carrier Sales

AI-powered inbound carrier-sales agent for Acme Logistics, built on the HappyRobot platform. A FastAPI backend handles carrier verification (FMCSA), load lookup, deterministic price negotiation, and call-record persistence. A React dashboard visualizes broker analytics. Single container, single deploy.

---

## Local development (two-terminal setup)

### Prerequisites

- Python 3.11+
- Node 18+
- A `.env` file in `backend/` (copy from `.env.example`)
- A `.env` file in `frontend/` (copy the `VITE_*` lines from `.env.example`)

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On first start the server creates `carrier_sales.db`, seeds 10 loads and 46 synthetic call records, then begins accepting requests. The API is available at `http://localhost:8000`.

### 2. Frontend (development mode with hot reload)

```bash
cd frontend
npm install
# Edit frontend/.env: set VITE_API_KEY to match LOADS_API_KEY in backend/.env
# VITE_API_BASE can stay empty — the Vite dev server proxies /metrics etc. to :8000
npm run dev
```

Open `http://localhost:5173` to see the dashboard with hot reload.

---

## Production build (single-origin, no proxy needed)

Build the SPA into `frontend/dist/`, then FastAPI serves both the API and the dashboard from port 8000.

```bash
# 1. Set the real API key in the frontend env
echo "VITE_API_KEY=<your LOADS_API_KEY>" > frontend/.env
echo "VITE_API_BASE=" >> frontend/.env

# 2. Build
cd frontend && npm install && npm run build && cd ..

# 3. Start the combined server
cd backend
uvicorn app.main:app --port 8000
```

Visit `http://localhost:8000` for the dashboard and `http://localhost:8000/metrics` for the raw API.

---

## Environment variables

### backend/.env

| Variable | Required | Description |
|----------|----------|-------------|
| `LOADS_API_KEY` | Yes | Full-access key. Used by the HappyRobot agent on write endpoints. Never send to the browser. |
| `READ_API_KEY` | Recommended | Read-only key accepted on GET endpoints. Baked into the browser bundle as `VITE_API_KEY`. If unset, read endpoints fall back to `LOADS_API_KEY`. |
| `FMCSA_API_KEY` | Yes | FMCSA QCMobile web key for carrier authority lookup |
| `DATABASE_URL` | No | SQLite path; defaults to `sqlite+aiosqlite:///./carrier_sales.db` |

Generate a key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### frontend/.env

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_KEY` | Yes | Must match `READ_API_KEY` (read-only). Do not use `LOADS_API_KEY` here. |
| `VITE_API_BASE` | No | Base URL of the API. Leave empty when same-origin (production build served by FastAPI). Set to `http://localhost:8000` only when running the Vite dev server separately. |

---

## Running tests

```bash
cd backend
python -m pytest tests/ -q
```

76 tests covering auth, loads, carrier verification, call upsert, negotiation logic, metrics aggregation, and seed idempotency.

---

## API endpoints

All endpoints require `X-API-Key` header.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/loads` | List loads (optional filters: equipment_type, origin, destination) |
| GET | `/loads/{load_id}` | Single load by ID |
| GET | `/verify-carrier/{mc_number}` | FMCSA authority check |
| POST | `/negotiate` | One round of deterministic price negotiation |
| POST | `/calls` | Upsert call record (HappyRobot webhook) |
| GET | `/metrics` | All dashboard aggregates (single payload) |

Full contract: `docs/API_CONTRACT.md`

---

## Architecture notes

- The backend is the source of truth. The AI agent talks; the backend decides all pricing and outcomes.
- `run_id` (HappyRobot's `current.run_id`) is the call key, threaded through every endpoint.
- Negotiation is deterministic and ceiling-bounded server-side; the agent passes only `{run_id, load_id, carrier_offer}`.
- The dashboard reads `GET /metrics` once on load. No polling, no websockets.
- `frontend/dist/` is served as static files by FastAPI at `/`; API routes take precedence.

Design decisions: `docs/DECISIONS.md`
