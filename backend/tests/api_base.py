"""Env-derived API base (ruled 2026-07-23, seed conversion 3b): the pinned
suite must run green against ANY environment — the preview host is
un-hardcoded across every test file. Order: process env (CI/prod override)
then frontend/.env (the environment's own URL)."""
import os

from dotenv import dotenv_values

_FE = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
API = f"{BASE_URL}/api"
