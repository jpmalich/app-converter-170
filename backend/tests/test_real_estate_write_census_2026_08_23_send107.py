"""SEND-107 PINS (Howard, 2026-08-23) — three invariants.

1. REAL-ESTATE WRITE CENSUS: no test may resolve a HARDCODED estimate id
   into a mutating operation. Hardcoded ids are, by construction, PRE-
   EXISTING estimates (runtime-created throwaways are never literals).
   The suite rebuilt the REAL Jon Casile estimate (EST-523061) in place
   for weeks through the founding-era pins and nothing caught it — this
   pin stops the next one. Reads stay lawful: live-invariant pins ARE
   the read layer. Register members carry an asserted reason.

2. ANTI-DEFAULT PIN: fails if `_ai_story_count` (the story ladder) or a
   numeric height floor ever returns to a priced gutter path — lexical
   AND functional (an empty `_verified_wall_heights_ft` MUST yield None
   for drop, mitre, clips and sealant). Same shape as the raw-wall-dim
   census pin. Without this, every test that exercised the default path
   now expects a refusal and nothing would catch the default coming back.

3. MONEY-WALK PAIRING: a MoneyWalk module without a refusal companion
   fails the suite — the pairing is pinned, not the instances, so the
   next walk someone adds cannot silently reopen the gap.
"""
import inspect
import re
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
BACKEND = TESTS.parent
sys.path.insert(0, str(BACKEND))

UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
CONST_RE = re.compile(
    r'^\s*([A-Za-z_][A-Za-z_0-9]*)\s*=\s*"([0-9a-f]{8}-[0-9a-f]{4}-'
    r'[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"')

# POST endpoints verified read-only (they compute or create a NEW doc,
# never write the addressed estimate): preview/compare/cost-preview have
# no estimates-write in their bodies; /duplicate reads the source and
# inserts a fresh id; /auth/login touches no estimate.
READONLY_POST = ("/lp-package/preview", "/lp-package/compare",
                 "/lp-package/cost-preview", "/duplicate", "/auth/login")

# REGISTERED NON-MEMBERS — each reason is ASSERTED against the file below.
REGISTER = {
    "test_fixture_protection.py":
        "guard pin — attempts the DELETE on the protected fixture and "
        "asserts the refusal; the write cannot land by construction",
    "test_tape_check_sheet_basis.py":
        "validation pins — both PUTs assert 400 rejection; nothing persists",
}


def _scan_violations():
    violations = []
    for p in sorted(TESTS.glob("test_*.py")):
        if p.name == Path(__file__).name:
            continue
        src = p.read_text()
        consts = {m.group(1) for line in src.splitlines()
                  if (m := CONST_RE.match(line))}
        for i, line in enumerate(src.splitlines(), 1):
            code = line.split("#", 1)[0]
            has_id = bool(UUID_RE.search(code)) or any(
                "{" + c + "}" in code for c in consts)
            has_db_write = any(
                re.search(r'estimates\.(update|replace|delete|insert)_one\(\s*\{\s*"id"\s*:\s*' + c + r'\b', code)
                for c in consts)
            if not has_id and not has_db_write:
                continue
            reason = None
            if re.search(r"\.(put|patch|delete)\(", code):
                reason = "mutating HTTP verb"
            elif ".post(" in code and not any(e in code for e in READONLY_POST):
                reason = "POST to a non-registered endpoint"
            elif re.search(r"estimates\.(update|replace|delete|insert)_one\(", code) and any(
                    re.search(r'"id"\s*:\s*' + c + r'\b', code) for c in consts):
                reason = "direct db write keyed by a hardcoded id"
            elif any(re.search(r"\b_?\w*(?:put|patch|delete|materialize|freeze|rederive|apply)\w*\s*\([^)]*\b" + c + r"\b", code, re.I)
                     for c in consts) and ".get(" not in code:
                # helper-call hole (found on test_iteration_48: `_put(sess, JON, …)`)
                reason = "hardcoded id passed into a mutating-named helper"
            if reason and p.name not in REGISTER:
                violations.append(f"{p.name}:{i} [{reason}] {line.strip()[:110]}")
    return violations


def test_no_test_resolves_a_real_estimate_id_into_a_write():
    v = _scan_violations()
    assert not v, (
        "SEND-107 REAL-ESTATE WRITE CENSUS: test(s) resolve a hardcoded "
        "(pre-existing, therefore real) estimate id into a mutating "
        "operation — use a disposable clone (tests/clone_util.py):\n"
        + "\n".join(v))


def test_register_reasons_hold():
    src = (TESTS / "test_fixture_protection.py").read_text()
    assert re.search(r"\.delete\(", src) and ("423" in src or "refus" in src.lower()), \
        "fixture-protection register reason no longer matches the code"
    src = (TESTS / "test_tape_check_sheet_basis.py").read_text()
    puts = [l for l in src.splitlines() if ".put(" in l]
    assert puts and src.count("status_code == 400") >= 2, \
        "tape-check register reason no longer matches the code (PUTs must assert 400)"


# ── 2. ANTI-DEFAULT PIN ────────────────────────────────────────────────

def _code_only(path: Path) -> str:
    return "\n".join(l.split("#", 1)[0] for l in path.read_text().splitlines())


def test_story_default_never_returns_lexically():
    for p in (BACKEND / "routes" / "hover.py", BACKEND / "lp_package.py"):
        code = _code_only(p)
        assert "_ai_story_count" not in code, (
            f"THE STORY LADDER IS BACK in {p.name} — Ruling V retired "
            "`_ai_story_count` from every priced path (SEND-105/107)")
    from routes import hover
    for fn in (hover._verified_drop_height_ft, hover._downspout_drop_ft,
               hover._gutter_corner_count):
        src = inspect.getsource(fn)
        code = "\n".join(l.split("#", 1)[0] for l in src.splitlines())
        assert "_ai_avg_wall_height_ft" not in code, fn.__name__
        assert not re.search(r"=\s*9\.0\b|\*\s*9\.0\b", code), (
            f"a 9-ft floor returned to {fn.__name__} (Ruling V retired it)")


def test_empty_verified_heights_refuse_functionally():
    from routes import hover
    m = {"eaves_lf": 184.0}
    assert hover._gutter_lf(m) > 0          # the height-free base stands
    assert hover._downspout_drop_ft(m) is None
    assert hover._downspout_lf(m) is None
    assert hover._gutter_corner_count(m) is None
    assert hover._mitre_count(m) is None
    assert hover._pipe_clips_count(m) is None
    assert hover._sealant_count(m) is None
    m2 = {**m, "_verified_wall_heights_ft": {"front": {"ft": 9.0, "src": "taped_human"}}}
    assert hover._downspout_drop_ft(m2) == 12.0   # verified 9 ft prices; a DEFAULT 9 ft never exists


def test_refusal_rows_carry_the_machine_code():
    from routes import hover
    assert hover.RULING_V_REFUSAL_CODE == "RULING_V_NO_VERIFIED_HEIGHT"
    src = (BACKEND / "routes" / "hover.py").read_text()
    assert '"not_derivable_code": RULING_V_REFUSAL_CODE' in src, (
        "refusal rows must carry the machine reason code — companions "
        "assert the code, never the prose sentence (SEND-107)")


# ── 3. MONEY-WALK PAIRING PIN ─────────────────────────────────────────

def test_every_money_walk_has_a_refusal_companion():
    walks = {}
    for p in sorted(TESTS.glob("test_*.py")):
        src = p.read_text()
        if re.search(r"class\s+\w*MoneyWalk", src) or re.search(r"def\s+test_\w*money_walk", src):
            walks[p.name] = bool(re.search(r"def\s+test_\w*refusal_companion", src))
    assert walks, "census expects at least one money walk (Casile)"
    missing = [n for n, ok in walks.items() if not ok]
    assert not missing, (
        "MONEY WALK WITHOUT A REFUSAL COMPANION (SEND-107) — the priced "
        f"path and the refusal path must BOTH stay covered: {missing}")
