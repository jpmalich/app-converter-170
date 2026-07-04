# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Siding Estimator — a supplier-distributed B2B SaaS built for Alside Supply. Contractors register with an access code, brand their company, build siding/window estimates for homeowners, and email quotes. FastAPI + MongoDB backend, React 19 (CRA + craco) frontend. Originally generated on the Emergent platform (docs sometimes reference `/app/...` paths — that's the container mount; locally the repo root is this directory).

`memory/PRD.md` is the living spec + detailed iteration history (features, defect fixes, prompt changes). Read the relevant section before touching the AI-measure pipeline. `test_result.md` has a protocol block at the top that must never be edited or removed.

## Commands

### Backend (`backend/`)
```bash
pip install -r requirements.txt
uvicorn server:app --reload --port 8001        # run (needs env vars, see below)
python -m pytest tests/                        # all tests
python -m pytest tests/test_run1_defects.py    # one file
python -m pytest tests/test_run1_defects.py -k test_name   # one test
ruff check .                                   # lint
```
Tests are designed to skip cleanly when env vars are absent, so most of the suite runs without a live Mongo or API keys.

### Frontend (`frontend/`)
```bash
yarn install       # yarn 1.22.x is pinned via packageManager
yarn start         # craco dev server
yarn build         # production build
npx eslint src     # lint (ESLint v9 flat config in eslint.config.js)
```

### Required environment
No `.env` files are committed. Backend **fails closed at import time** without: `MONGO_URL`, `DB_NAME`, `JWT_SECRET` (≥32 chars), `ADMIN_PASSWORD`, and `CORS_ORIGINS` (empty list = all preflights refused; never add `*`). Optional: `SIGNUP_CODE`, `SUPPLIER_ADMIN_TOKEN`, `RESEND_API_KEY`, `JWT_TTL_SECONDS`, `ANTHROPIC_API_KEY` (routes Claude calls directly instead of through the Emergent LiteLLM proxy — backend-only, must never appear in frontend code; a test enforces this). Frontend needs `REACT_APP_BACKEND_URL` (API client prepends `/api`).

## Architecture

### Backend
`server.py` is a thin entrypoint: loads `.env`, mounts CORS, includes `routes.api_router`. All business logic lives elsewhere:

- `routes/` — one router per domain, composed under the `/api` prefix in `routes/__init__.py`. Notable: `ai_measure.py` (the largest — AI photo-measurement pipeline), `estimates.py`, `auth.py`, `catalog.py`, plus per-product-line routers (`mezzo.py`, `vero.py`, `iss.py`, `lp_admin.py`, `hover.py`).
- `config.py` — all env-driven constants, imported everywhere. Validation happens at import.
- `db.py` — shared Motor (async Mongo) client + logger.
- `services.py` — `calc_totals` and other shared business logic; `models.py` — Pydantic models; `deps.py` — auth dependencies; `startup.py` — seeding on app start.
- Catalog seed data: `catalog_seed.py` (default Alside catalog), `mezzo_catalog.py`/`vero_catalog.py`/`iss_catalog.py` + their `*_prices.py`/`*_seed_prices.json`, `lp_smartside_formulas.py`.

**Auth model (three tiers):**
1. Public — `GET /api/branding` only.
2. Supplier admin — `X-Admin-Token` header (never query string; that was removed as SEC-006) for `/api/admin/*`.
3. Contractors — JWT in an httpOnly cookie (`withCredentials` axios), multi-tenant scoped per company. New companies need `SIGNUP_CODE`; teammates join via an 8-char invite code.

**Route-ordering gotcha:** literal paths (e.g. CSV exports) are registered before `/estimates/{est_id}` so they win FastAPI matching — preserve that ordering when adding routes.

**AI-measure pipeline** (`routes/ai_measure.py`): a two-phase (Phase A extraction per photo → Phase B reconcile) Claude vision pipeline that turns contractor photos into wall/opening/dormer measurements. Runs as a background worker writing status onto a run doc that the frontend polls; sessions autosave via `ai_measure_sessions.py`. It has an extensive regression suite in `backend/tests/` (`test_two_phase_pipeline.py`, `test_run1_defects.py`, `test_dormers_array_end_to_end.py`, etc.) — hardened against real-run defects documented in PRD.md. Empty extractions retry once and are surfaced, never silently dropped.

### Frontend
CRA + craco with `@` aliased to `src/`. shadcn/Radix primitives live in `src/components/ui/`.

- `src/App.js` — all routing. Provider nesting: `LangProvider > AuthProvider > BrandingProvider > CompanyProvider`. `BrandingProvider` is public (login page); `CompanyProvider` is auth'd.
- **Workspaces:** the app is multi-product — `/dashboard/siding`, `/dashboard/lp_smart`, `/dashboard/windows`, `/dashboard/iss` all render `Dashboard` with a `kind` prop; estimates carry a `kind` and `GET /api/estimates?kind=` filters per workspace. `EstimateRouter` dispatches an estimate id to the right editor.
- `src/lib/` — `api.js` (axios instance, `withCredentials: true`), `calc.js`/`wasteLogic.js`/`materialList.js` (client-side estimate math), context providers, i18n.
- `src/components/estimate/` — the estimate editor's building blocks. `AIMeasureButton.jsx` (AI-measure modal, polling, session resume, error banners) and `HouseModel3D.jsx` (Three.js parametric house render from AI output) are the most intricate.
- Interactive elements carry `data-testid` attributes — keep adding them for new UI; the testing agent relies on them.
- **SSOT rule:** the 3D view and side panels read backend-computed values (`preview.measurements._per_elevation_breakdown`, `preview.lines[]`) — do not re-implement material math client-side.

## Code quality conventions (see CODE_QUALITY.md — authoritative)

Linter configs are deliberately pinned: Ruff selects only `E, W, F` with documented ignores (`pyproject.toml`), ESLint enables the react-hooks rules that catch real bugs. This project **explicitly rejects** review findings about: cyclomatic complexity / "function too long", missing type hints, `Optional[X]` vs `X | None`, hardcoded creds in `tests/` (fixtures), `is None` idioms, and Provider-value memoization noise. If an automated review flags something the pinned configs don't, treat it as noise. Run both linters before submitting changes.

## Testing protocol

`test_result.md` is the communication channel between the main agent and a testing agent: update task statuses there **before** invoking testing, keep the YAML structure, and never modify the protocol block at the top of the file.
