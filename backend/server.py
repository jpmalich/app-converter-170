"""FastAPI entrypoint. Wires CORS, sub-routers, and startup tasks. All business
logic now lives in `routes/`, `services.py`, `startup.py`, etc."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Iter 79j.49 — Ring-buffer log handler MUST be attached before any
# other module is imported, because module-level `logger.info(...)`
# calls (like the AI_MEASURE key-routing summary in routes/ai_measure.py)
# fire at import time. Attach the handler first, THEN import routers.
import logging  # noqa: E402
from collections import deque  # noqa: E402


class _RingBufferLogHandler(logging.Handler):
    """Retains the most recent N formatted log records."""

    def __init__(self, capacity: int = 2000) -> None:
        super().__init__()
        self.buffer: deque[str] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.append(self.format(record))
        except Exception:
            pass


LOG_RING = _RingBufferLogHandler(capacity=2000)
LOG_RING.setLevel(logging.INFO)
LOG_RING.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
))
# db.py calls logging.basicConfig(level=INFO) at import time, but
# basicConfig is a no-op if handlers are already attached. Prime the
# root logger BEFORE anything else imports so basicConfig doesn't
# steamroll our ring buffer.
_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
_root_logger.addHandler(LOG_RING)

from fastapi import FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from config import CORS_ORIGINS  # noqa: E402
from db import client  # noqa: E402
from routes import api_router  # noqa: E402
from startup import run_startup  # noqa: E402


app = FastAPI(title="Vinyl Siding Estimator API")
app.include_router(api_router)

# SEC-001 — Iter 78z+++: never combine `*` with credentials. The
# Starlette CORS middleware reflects the request Origin when set to
# `*` + credentials, which lets any 3rd-party site read tenant data
# with the auth cookie. Strip any wildcard out and require an explicit
# allowlist; if the env var was empty, the list is empty and every
# preflight is refused (fail closed).
_allowed_origins = [o for o in CORS_ORIGINS if o != "*"]
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Iter 79j.49 — Platform health probe. The Emergent platform hits
# GET /health (NOT /api/health) every ~2s and interprets 404 as pod
# unhealthy → may restart the pod. This route lives OUTSIDE the /api
# prefix by design; do NOT move it under the api_router.
@app.get("/health")
async def platform_health():
    return {"status": "ok"}


@app.on_event("startup")
async def on_start():
    await run_startup()


@app.on_event("shutdown")
async def shutdown():
    client.close()
