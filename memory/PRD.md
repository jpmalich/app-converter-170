# Vinyl Siding Estimator — PRD

## Original Problem
User uploaded a self-contained HTML "Vinyl Siding Estimator" used by Wolf and Son Renovations LLC and asked: "what do i need to do with the attached html to make it an app". User selected: installable PWA + Web app (React/FastAPI/MongoDB), persistence + saved estimate list, multi-user JWT login, edit catalog from UI, photo uploads (local disk), email quote via Resend (key deferred), modernize design.

## Architecture
- Backend: FastAPI + MongoDB (motor), bcrypt + PyJWT cookie auth (httpOnly, secure, samesite=none), Resend SDK lazy-loaded for email
- Frontend: React 19 + react-router-dom v7 + Tailwind + sonner toasts + lucide-react icons, installable PWA (manifest + sw.js), Archivo + JetBrains Mono fonts
- Storage: MongoDB collections `users`, `catalogs` (single global), `estimates` (per-user). Photos on disk under `/app/backend/uploads/` served via `/api/uploads/{name}`
- Routing: All backend endpoints under `/api`; frontend calls `${REACT_APP_BACKEND_URL}/api`

## User Personas
- **Contractor / Estimator** (primary): on a phone/tablet at jobsite typing quantities; needs live Sell Price & Profit always visible; needs to email quote to homeowner
- **Owner / Admin**: edits price catalog when material costs shift; reviews team estimates

## Core Requirements (Static)
1. Multi-user JWT email/password authentication
2. Persist estimates per-user with full snapshot (line item qtys, settings, photos)
3. Editable shared price catalog seeded with the 60+ items from the original HTML
4. Live recalculation: Base, Sell Price, Profit update on every keystroke
5. Customer-facing printable + emailable quote
6. Photo uploads attached to a job
7. Installable PWA (mobile-first ergonomics, sticky totals bar)

## Implemented (2026-05-23)
- ✅ Auth: register / login / logout / me with httpOnly cookies, admin auto-seeded (`admin@wolfandson.com` / `Admin123!`)
- ✅ Catalog GET/PUT/reset with 10 sections × 60+ items from original SECTIONS array
- ✅ Estimate CRUD with per-user isolation
- ✅ Live calc: subMat → +waste → +tax → +labor → base → +margin → sell → profit
- ✅ Sticky black/orange sell-bar (Base / Sell / Profit) on editor
- ✅ Collapsible section accordions with desktop grid + mobile-friendly inputs
- ✅ Job photo upload (≤10MB) + thumbnail + remove
- ✅ Customer Quote modal — printable, brutalist invoice look, email button gated by Resend config
- ✅ Catalog manager screen (edit prices, add/remove items, reset to defaults)
- ✅ PWA manifest + service worker + icons
- ✅ Modernized design: Archetype 4 Swiss + Industrial Tech (stark white / safety-orange / black, Archivo + JetBrains Mono)
- ✅ Backend testing: 17/17 pytest tests passed
- ✅ Frontend testing: 16/16 E2E scenarios passed
- ✅ CORS tightened to explicit origins; logout cookie clear attributes fixed

## Mocked / Deferred
- ⚠️ Resend email: endpoint wired up, returns 503 with helpful message until user adds `RESEND_API_KEY` to `backend/.env`. UI shows an amber "not configured" notice and disables Send.

## Prioritized Backlog
### P1
- [ ] Resend API key paste → live quote email
- [ ] Internal PDF export (server-side render so it's identical to print)
- [ ] Misc-line ad-hoc rows in editor (the original HTML supported free-form description per category)

### P2
- [ ] Multi-tenant catalog (per company instead of single global)
- [ ] Estimate templates / duplicate
- [ ] Customer / contact directory
- [ ] CSV export of estimates for QuickBooks
- [ ] Role-based catalog edit gating (only admin)

### Nice-to-haves
- [ ] Refactor EstimateEditor.jsx (~425 lines) into smaller components and a `useEstimate` hook
- [ ] Lifespan event handlers instead of deprecated `on_event`
- [ ] MIME validation on uploads beyond extension check
