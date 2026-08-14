"""SKIP REASON CLASS REGISTRY + BUILD-FAIL PIN
Howard ruled 2026-08-13 (pro-quotes reply 4, approval 2):

  "Every skip declares a reason from a known class — tombstone,
   cadence-gated, environment-gated. THE BUILD FAILS ON AN
   ANONYMOUS SKIP. That is the registry-plus-census pattern
   applied to skips, and it is the same move that has now caught
   something on its first run for seams, TTL indexes, schema
   consumers, surfaces and normalizer fields. A skip should never
   again be a thing nobody can name."

The pin fires the moment a new `pytest.skip(...)` reason string
does not begin with one of the registered class tags. A pin
elsewhere already registers the FIVE baseline skips (four
cadence-gated ingress smokes + one tombstone before it was
inverted); this file's registry names the CLASSES those skips
may declare themselves under.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = BACKEND_ROOT / "tests"


# ---------------------------------------------------------------------
# REGISTRY — the ONLY reason-string prefixes allowed on a `pytest.skip`
# ---------------------------------------------------------------------
# Format: reason string MUST begin with one of these tags followed by
# a colon and a human description. Anything else is anonymous ⇒ build
# fails. This is the same shape as seam_accounting.SEAM_REGISTRY: the
# registry names the LEGAL classes, the census finds the concrete
# calls, the pin cross-checks that every call declares its class.
SKIP_REASON_CLASSES = {
    "tombstone":
        "A test kept as a marker against an obsolete contract we "
        "explicitly ruled out. PREFERRED SHAPE is a positive "
        "assertion of the current contract (see the send-11 "
        "pro-quotes-reply-4 inversion of the iter-6 material-"
        "override tombstone into a live SHAPE assertion). Use "
        "`tombstone:` only when the current contract has no "
        "assertable positive form (rare).",
    "cadence:tape_check":
        "Runs on the handback cadence via TEST_API_EXTERNAL=1 — "
        "the same cadence the ingress smoke rides. The env var is "
        "named on the skip line; the handback script sets it "
        "before invoking pytest, so these DO run when they must "
        "(the stamp prints their result).",
    "cadence:external":
        "Runs only when the tester deliberately opts in for an "
        "external round-trip (e.g. `TEST_API_EXTERNAL=1`). Not "
        "gated by ingress but by an explicit tester action. Skipped "
        "in every default local + CI run.",
    "env:mongo":
        "Requires a live Mongo the current process can reach. Not "
        "the shared motor client — a scratch collection with its "
        "own sync client. Skip only when the env explicitly cannot "
        "provide one.",
    "env:live_auth":
        "Requires the pod's live auth stack (email login + cookie "
        "session). Test env-gated because a container without seeded "
        "credentials cannot exercise it — see test_guard_extension "
        "for the passing shape when auth IS available.",
    "env:llm_key":
        "Requires the EMERGENT_LLM_KEY (or provider-specific key) "
        "to reach an LLM. Skip when the key isn't provisioned; the "
        "test is real work, not a mock.",
    "env:signup_code":
        "Requires SIGNUP_CODE / SUPPLIER_ADMIN_TOKEN in the process "
        "env to sign up a fresh account. iteration-5/6 tenant "
        "tests use these; local dev envs typically don't provision "
        "them.",
    "env:fixture_estimate":
        "Requires a specific estimate to exist on the session's "
        "account (EST-886440, a non-untouchable estimate, etc). "
        "Skipped when the fixture estimate is not present — cost "
        "of running is a re-seed, not a code change.",
    "env:fixture_data":
        "Requires seeded fixture data (Haugh hover run, LP rows on "
        "a specific job, demo staging). Data has a TTL or a "
        "manual staging step; skipped when absent — re-stage to "
        "restore the pin substrate.",
    "env:fixture_ledger":
        "Requires a ledger of a minimum size to exercise walkability "
        "(pagination disjoint pin, full walk). Skipped when the "
        "ledger is too small on the current account — grow the "
        "fixture ledger to exercise.",
    "env:backend_url":
        "Requires REACT_APP_BACKEND_URL to be set so the test can hit "
        "the same external URL the frontend does. Skipped when the "
        "env is missing; the fix is to source frontend/.env, not to "
        "write the test differently.",
    "ruling:held":
        "A RULING that is on the record but NOT YET BUILD-ABLE (Ruling C, "
        "sealed 2026-08-14 send-14: 'a ruling that is HELD enters as a "
        "VISIBLE NAMED SKIP stating why it is held and what would unhold "
        "it. It shows in every run as on-the-record-and-unbuilt.'). The "
        "skip reason MUST state what would unhold it. This is how a held "
        "ruling can never silently vanish between sends.",
}


# ---------------------------------------------------------------------
# The pin — AST walk to find every skip call in the tests dir
# ---------------------------------------------------------------------
_SKIP_CALL_NAMES = {"skip", "pytest.skip"}
_REASON_PREFIX_RE = re.compile(
    r"^\s*(?P<tag>[a-z_][a-z0-9_]*(?::[a-z_][a-z0-9_]*)?)\s*[:\-]"
)


def _find_skip_calls_in_file(path: Path) -> list[tuple[int, str | None]]:
    """Return [(lineno, reason_string_or_None), ...] for every
    `pytest.skip(...)` or `@pytest.mark.skip(reason=...)` call. A
    dynamic reason (variable, f-string, computed) yields None."""
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError:
        return []
    hits: list[tuple[int, str | None]] = []

    def _reason_from_call(node: ast.Call) -> str | None:
        """Return the LEADING literal portion of the reason string —
        enough to classify the tag. An f-string that STARTS with a
        constant tag prefix (e.g. `env:live_auth: {err}`) is
        classifiable; a fully-computed reason (a bare variable, or
        an f-string with a leading `{...}`) returns None."""
        def _lead_from(v):
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                return v.value
            if isinstance(v, ast.JoinedStr) and v.values:
                first = v.values[0]
                if isinstance(first, ast.Constant) and \
                        isinstance(first.value, str):
                    return first.value
            return None
        # Kwargs first (reason=...)
        for kw in node.keywords:
            if kw.arg == "reason":
                return _lead_from(kw.value)
        # Then positional first arg
        if node.args:
            return _lead_from(node.args[0])
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = None
        if isinstance(fn, ast.Attribute):
            # pytest.skip(...) OR pytest.mark.skip(reason=...)
            if fn.attr == "skip":
                if (isinstance(fn.value, ast.Name)
                        and fn.value.id == "pytest"):
                    name = "pytest.skip"
                elif (isinstance(fn.value, ast.Attribute)
                        and fn.value.attr == "mark"
                        and isinstance(fn.value.value, ast.Name)
                        and fn.value.value.id == "pytest"):
                    name = "pytest.mark.skip"
        elif isinstance(fn, ast.Name) and fn.id == "skip":
            name = "skip"
        if name in _SKIP_CALL_NAMES or name == "pytest.mark.skip":
            hits.append((node.lineno, _reason_from_call(node)))
    return hits


def _classify(reason: str) -> str | None:
    """Return the registered tag if `reason` starts with one, else None.
    Prefix format: '<tag>:<space><description>' — a leading tag
    matched against SKIP_REASON_CLASSES, followed by ':' or '-'."""
    m = _REASON_PREFIX_RE.match(reason)
    if not m:
        return None
    tag = m.group("tag").lower()
    return tag if tag in SKIP_REASON_CLASSES else None


# ---------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------

def test_skip_reason_class_registry_is_populated():
    """The registry MUST name at least the classes the baseline five
    skips declare against — one tombstone + one cadence tag. Adding a
    new class to the registry is an explicit ruling; removing one
    without inverting/retiring the callers must fail loud."""
    assert "tombstone" in SKIP_REASON_CLASSES
    assert "cadence:tape_check" in SKIP_REASON_CLASSES


def test_every_skip_in_the_suite_declares_a_registered_class():
    """AST-walk every test file. Every `pytest.skip(...)` /
    `@pytest.mark.skip(reason=...)` reason string MUST begin with a
    tag from SKIP_REASON_CLASSES followed by `:` or `-`. A dynamic
    reason (variable, f-string) is allowed IF the string is empty
    (nothing to classify) — the caller must self-document with a
    comment; that softer requirement is a follow-up for the census
    file. Anonymous constant reasons fail here."""
    violations: list[str] = []
    for py in TESTS_DIR.rglob("test_*.py"):
        if py.name == Path(__file__).name:
            continue
        for lineno, reason in _find_skip_calls_in_file(py):
            if reason is None:
                # Dynamic — the pin does not catch dynamic reasons.
                # A separate census (below) records them for review.
                continue
            if _classify(reason) is None:
                violations.append(
                    f"{py.relative_to(BACKEND_ROOT)}:{lineno} — "
                    f"anonymous skip reason (must start with a "
                    f"registered class tag from "
                    f"{sorted(SKIP_REASON_CLASSES)}): {reason!r}")
    assert not violations, (
        "SEND-11 pro-quotes-reply-4 rule: every skip declares a "
        "known class. Fix by prefixing the reason with a tag "
        "(e.g. 'tombstone: ...' or 'cadence:tape_check: ...') OR "
        "invert the skip into a positive assertion (see the "
        "test_material_overrides_are_structurally_impossible "
        "inversion of the iter-6 tombstone as the pattern).\n"
        + "\n".join(violations))


def test_dynamic_skip_reasons_are_registered_or_absent():
    """Skips whose reason is a non-constant expression (variable,
    f-string, function call) cannot be classified statically. They
    are permitted ONLY when named on a small allowlist — the file
    path they occur in is the identity. Empty allowlist right now;
    adding one is a ruling, same as adding a seam."""
    ALLOWED_DYNAMIC_SKIP_FILES: set[str] = {
        # Add file paths (relative to backend/) here when a dynamic
        # skip is legitimately unclassifiable — with a comment
        # naming the ruling. Kept empty on purpose.
    }
    violations: list[str] = []
    for py in TESTS_DIR.rglob("test_*.py"):
        if py.name == Path(__file__).name:
            continue
        rel = str(py.relative_to(BACKEND_ROOT))
        for lineno, reason in _find_skip_calls_in_file(py):
            if reason is None and rel not in ALLOWED_DYNAMIC_SKIP_FILES:
                violations.append(
                    f"{rel}:{lineno} — dynamic skip reason (add the "
                    f"file to ALLOWED_DYNAMIC_SKIP_FILES with a "
                    f"ruling comment, OR replace the dynamic reason "
                    f"with a constant classified string)")
    assert not violations, (
        "SEND-11 pro-quotes-reply-4 rule (dynamic-reasons variant): "
        "unclassified dynamic skip reasons are refused.\n"
        + "\n".join(violations))
