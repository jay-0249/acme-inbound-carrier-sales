# =============================================================================
# Stage 1 — build the React SPA
# =============================================================================
FROM node:20-slim AS frontend

WORKDIR /frontend

# Copy manifests first so npm ci is cached unless dependencies change
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy the rest of the frontend source
COPY frontend/ .

# Vite bakes VITE_* vars into the bundle at build time; supply them as ARGs
ARG VITE_API_KEY
ARG VITE_API_BASE=""
ENV VITE_API_KEY=$VITE_API_KEY
ENV VITE_API_BASE=$VITE_API_BASE

RUN npm run build
# Produces /frontend/dist


# =============================================================================
# Stage 2 — Python runtime (FastAPI serves API + built SPA)
# =============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install Python deps first (cached unless requirements.txt changes)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source (tests excluded via .dockerignore)
COPY backend/ .

# Copy the built SPA to the path main.py expects.
# main.py resolves: Path(__file__).parents[2] / "frontend" / "dist"
# In the container __file__ = /app/app/main.py, so parents[2] = / -> /frontend/dist
COPY --from=frontend /frontend/dist /frontend/dist

EXPOSE 8000

# Railway injects $PORT at runtime; default to 8000 for local docker run.
# SQLite DB is created at /app/carrier_sales.db on first start, seeded
# automatically via the lifespan handler. The filesystem is ephemeral on
# Railway — data resets on redeploy (acceptable for this demo POC).
# For persistence, mount a Railway volume at /app and set DATABASE_URL
# to a file path inside it (future work).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
