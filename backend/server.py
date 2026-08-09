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

# R3 EVIDENCE SURVIVES RESTART (Howard ruled 2026-08-07): the ring is
# in-memory — a restart during a demo would destroy exactly the evidence
# R3 exists to keep. WARNING+ also lands on disk.
from logging.handlers import RotatingFileHandler  # noqa: E402

WARN_LOG_PATH = "/var/log/pro_quotes_warnings.log"
_WARN_SINK = RotatingFileHandler(WARN_LOG_PATH, maxBytes=1_000_000,
                                 backupCount=2)
_WARN_SINK.setLevel(logging.WARNING)
_WARN_SINK.setFormatter(logging.Formatter(
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
_root_logger.addHandler(_WARN_SINK)

from fastapi import FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from config import CORS_ORIGINS  # noqa: E402
from db import client  # noqa: E402
from routes import api_router  # noqa: E402
from startup import run_startup  # noqa: E402


app = FastAPI(title="Vinyl Siding Estimator API")
app.include_router(api_router)

# STALE PAGE DETECTION (Howard ruled 2026-08-09): the client compares the
# build it loaded with against this — a page older than the deployed
# build tells the user plainly and prompts a refresh. No auth: the login
# page is as capable of being stale as any other.
from build_version import get_build_version  # noqa: E402


@app.get("/api/version")
async def api_version():
    return {"version": get_build_version()}


# R3 (Howard ruled 2026-08-06): a failing request body names its field,
# validation and layer SERVER-SIDE — log-only on failure, nothing
# contractor-visible, response shape unchanged.
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.exception_handlers import (  # noqa: E402
    request_validation_exception_handler,
)


@app.exception_handler(RequestValidationError)
async def _log_validation_reject(request, exc):
    for e in exc.errors()[:10]:
        logging.warning(
            "VALIDATION REJECT %s %s — field=%s err=%s layer=pydantic-request",
            request.method, request.url.path,
            ".".join(str(p) for p in e.get("loc", ())), e.get("msg"))
    return await request_validation_exception_handler(request, exc)


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
