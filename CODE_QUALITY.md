# Code Quality Standards

This project pins explicit linter configs so automated reviews don't surface
false positives. **If a code-review tool flags something not caught here, that
flag is noise — push back, do not refactor working code.**

## Frontend (ESLint v9 flat config)
- Config: `/app/frontend/eslint.config.js`
- Run: `cd /app/frontend && npx eslint src`
- Required deps: `globals`, `eslint-plugin-react`, `eslint-plugin-react-hooks` (already installed)
- **Real rules that catch bugs**: `react-hooks/rules-of-hooks` (error), `react-hooks/exhaustive-deps` (warn), `no-unused-vars`, `no-undef`, `no-dupe-keys`, `no-unreachable`
- **Intentionally disabled noise**: `react/prop-types`, `react/no-unescaped-entities`

## Backend (Ruff)
- Config: `/app/backend/pyproject.toml`
- Run: `cd /app/backend && ruff check .`
- Selects: `E, W, F` — pycodestyle errors/warnings + pyflakes (real bugs only)
- **Explicitly ignored** (with reasoning in `pyproject.toml`):
  - `E501` line-too-long — not a bug
  - `E711`/`E712` — we use `is None` correctly, suppress confused reviewers
  - `E402` — `load_dotenv()` must run before config imports in `server.py`

What we deliberately do NOT enable (and why): complexity (`C901`, `PLR*`), `UP*` PEP-604 modernization, `RUF001` ambiguous-unicode (em-dashes are intentional), `S` security (false positives on test fixtures), `ANN*` type hints (not required), `D*` docstrings.

## What automated reviewers should NOT flag
1. **Complexity / "function too long"** — straight-line logic is fine.
2. **Missing type hints** — not required.
3. **Hardcoded creds in `tests/`** — test fixtures, not secrets. Tests skip cleanly when env vars are absent.
4. **`is None` patterns** — correct Python idiom.
5. **Inline objects in Provider value** — already memoized where it matters; over-memoizing primitive contexts is noise.

## What we DO care about
- React hook dependency mistakes (`react-hooks/exhaustive-deps`)
- Undefined variables / unused imports (Pyflakes `F`)
- Likely-bug patterns (Bugbear `B`)
- Security issues from user-controlled input (`S` selectively, mostly handled by FastAPI/Pydantic)
- Real lint errors that prevent the app from running

Run both linters locally before submitting changes. The CI / automated reviewer
should defer to these configs.
