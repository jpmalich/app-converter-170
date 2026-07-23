"""Test-credential loader. STANDING RULE (2026-07-16): secrets live ONLY in
backend/.env — never hardcoded in code, tests, chat, or memory files."""
from pathlib import Path

from dotenv import dotenv_values

_ENV = dotenv_values(Path(__file__).resolve().parent / ".env")
TEST_EMAIL = _ENV.get("ADMIN_EMAIL", "")
TEST_PASSWORD = _ENV.get("ADMIN_PASSWORD", "")

# COMPANY-SLOT SPLIT (ruled 2026-07-23, seed conversion): on prod the
# test-only fixtures (doug jones, haugh, round-two) seed under a SEPARATE
# test company so the demo account's estimates list stays demo-appropriate
# (Letrick, red house, demo). The suite targets each fixture's company via
# these pairs; in preview both default to the same account (no split here).
FIXTURE_DEMO_EMAIL = _ENV.get("FIXTURE_DEMO_EMAIL") or TEST_EMAIL
FIXTURE_DEMO_PASSWORD = _ENV.get("FIXTURE_DEMO_PASSWORD") or TEST_PASSWORD
FIXTURE_TEST_EMAIL = _ENV.get("FIXTURE_TEST_EMAIL") or TEST_EMAIL
FIXTURE_TEST_PASSWORD = _ENV.get("FIXTURE_TEST_PASSWORD") or TEST_PASSWORD
