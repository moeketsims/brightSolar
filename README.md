# Bright Solar Power — Operations App

Management app for Bright Solar Power: track clients, prioritise incoming jobs
by estimated profitability, and record every expense (diesel, consumables,
travel, labour) against the job it belongs to.

## Stack

- **Backend**: FastAPI + SQLAlchemy 2 (async) + PostgreSQL — runs in Docker
- **Frontend**: Next.js 15 (App Router) + TypeScript + Tailwind — runs natively on Windows for dev
- **DB admin**: pgAdmin at http://localhost:5050

### Why isn't the frontend in Docker?

Local dev only: Next.js hot reload + `node_modules` on Windows bind mounts is
slow and flaky (file-watch polling). Running `npm run dev` on the host is
faster and easier to debug. A production `frontend/Dockerfile` is included so
you can containerise for deployment later.

## First-time setup

```bash
# 1. Start backend + database (first run builds the image, ~1 min)
docker compose up -d --build

# 2. Seed some sample data so the UI isn't empty
docker compose exec backend python -m app.seed

# 3. Install and start the frontend (separate terminal)
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

## What's running where

| Service  | URL                         | Notes                              |
| -------- | --------------------------- | ---------------------------------- |
| Frontend | http://localhost:3000       | `npm run dev` on host              |
| API      | http://localhost:8001       | Swagger UI at `/docs`              |
| Postgres | localhost:5432              | user/pass/db all `brightsolar`     |
| pgAdmin  | http://localhost:5050       | admin@brightsolar.local / admin    |

## Domain model

- **Client** — name, phone, address, lat/lng
- **Job** — belongs to a client. Has `estimated_revenue`, `estimated_cost`,
  `distance_km`, `urgency`, `status`, `scheduled_date`, and an optional manual
  `priority_override`.
- **Expense** — belongs to a job. Categorised: `diesel`, `consumable`,
  `travel`, `labour`, `equipment`, `other`.

### Priority scoring

```
score = (est_revenue - est_cost) - (distance_km × R3.50 × 2 round-trip) + urgency_boost
```

Urgency boost: `low=0`, `normal=100`, `high=500`, `critical=2000`.
You can override with `priority_override` on the job. Higher score = do first.
Tune the coefficient in `backend/app/priority.py` once you know your real
diesel cost per km.

## Key API endpoints

```
GET    /dashboard                    summary + top-5 priority jobs
GET    /clients                      list clients
POST   /clients                      create client
GET    /jobs?status=new              list jobs (sorted by priority desc)
POST   /jobs                         create job
GET    /jobs/{id}                    detail with expenses + totals
PATCH  /jobs/{id}                    update status, actual_revenue, etc.
POST   /jobs/{id}/expenses           log an expense
```

## Development

- Backend auto-reloads on code changes (volume-mounted `./backend/app`).
- Schema changes: for now, tables are auto-created on startup via
  `Base.metadata.create_all`. Add Alembic when the schema stabilises.
- Frontend uses a thin fetch client in `frontend/src/lib/api.ts`. All calls go
  directly to `NEXT_PUBLIC_API_URL` (default `http://localhost:8001`).

## Tearing down

```bash
docker compose down           # stops containers, keeps data
docker compose down -v        # also wipes the postgres volume
```
