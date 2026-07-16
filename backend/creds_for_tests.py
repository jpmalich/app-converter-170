"""Test-credential loader. STANDING RULE (2026-07-16): secrets live ONLY in
backend/.env — never hardcoded in code, tests, chat, or memory files."""
from pathlib import Path

from dotenv import dotenv_values

_ENV = dotenv_values(Path(__file__).resolve().parent / ".env")
TEST_EMAIL = _ENV.get("ADMIN_EMAIL", "")
TEST_PASSWORD = _ENV.get("ADMIN_PASSWORD", "")
