"""SEND-125 pins (Howard authorized 2026-08-24) — THE CLAIM DISTINCTION
IS ENFORCED BY DATA, NOT BY MEMORY.

Two pins, same shape as the no-job-names and prompt-purity disciplines:

(b) LEXICAL PIN — no report, prompt, comment or docstring may ASSERT the
    unearned claim ("reads unfamiliar sets", "generalizes to unfamiliar
    sets", ...). Recording the claim as NOT earned is legal: a hit must
    carry a negation marker on its own line or within the three lines
    above it. In PROMPT constants the phrases are banned outright — the
    model is never told it reads unfamiliar sets.
    The ban is COUPLED to the scoreboard: if the figures ever earn the
    read-claim, earned_claim() flips and the ban lifts by itself.

(c) SCOREBOARD PIN — the earned claim is computed from
    foreign_drafter_scoreboard (Dart 0/4, Tanis 0/4 → fails-safe only).
"""
import ast
import os
import re

from foreign_drafter_scoreboard import (
    CLAIM_FAILS_SAFE, CLAIM_READS, FOREIGN_DRAFTER_SCOREBOARD,
    drafters_emitting, earned_claim, read_claim_earned, unattributed_lanes,
)

UNEARNED_CLAIM_PATTERNS = [
    r"reads? (?:unfamiliar|foreign|unseen)\b",
    r"generali[sz]es (?:to|across|on)\b",
    r"generali[sz]ation (?:claim )?(?:is |has been )?earned",
    r"reads any (?:set|drawing|drafter)",
    r"drafter[- ]agnostic",
    r"works on unfamiliar",
]
NEGATION_MARKERS = [
    "not earned", "unearned", "not yet", "is not", "it is not",
    "does not", "no longer", "not:", "never", "cannot", "not a claim",
    "not authorized", "not proven", "would be", "if the figures",
]
PROMPT_MODULES = [
    "/app/backend/routes/ai_blueprint.py",
    "/app/backend/routes/ai_measure.py",
    "/app/backend/schedule_read.py",
    "/app/backend/height_read.py",
]
SCAN_ROOTS = [
    ("/app/memory", (".md",)),
    ("/app/backend", (".py",)),
    ("/app/frontend/src", (".js", ".jsx")),
]
# the registry DEFINES both claim strings as data — it is the source the
# pin computes from, not prose making a claim.
EXEMPT = {os.path.abspath(__file__),
          "/app/backend/foreign_drafter_scoreboard.py"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "backups", "evidence"}


def _files():
    for root, exts in SCAN_ROOTS:
        for dirpath, dirnames, names in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for n in names:
                if n.endswith(exts):
                    p = os.path.join(dirpath, n)
                    if os.path.abspath(p) not in EXEMPT:
                        yield p


def _hits(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        low = line.lower()
        for pat in UNEARNED_CLAIM_PATTERNS:
            if re.search(pat, low):
                context = " ".join(lines[max(0, i - 3):i + 1]).lower()
                if not any(m in context for m in NEGATION_MARKERS):
                    yield i + 1, line.strip()
                break


def test_no_prose_asserts_the_unearned_claim():
    assert not read_claim_earned(), (
        "scoreboard now earns the read-claim — this pin's ban lifts by "
        "itself; update the pin deliberately")
    bad = []
    for path in _files():
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for ln, line in _hits(text):
            bad.append(f"{path}:{ln} {line}")
    assert not bad, (
        "UNEARNED CLAIM ASSERTED — the figures say "
        f"{earned_claim()!r} only:\n" + "\n".join(bad))


def test_prompts_never_carry_the_claim_at_all():
    bad = []
    for path in PROMPT_MODULES:
        try:
            src = open(path, encoding="utf-8").read()
        except FileNotFoundError:
            continue
        for node in ast.walk(ast.parse(src)):
            if (isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and len(node.value) > 400):
                low = node.value.lower()
                for pat in UNEARNED_CLAIM_PATTERNS:
                    if re.search(pat, low):
                        bad.append(f"{path}:{node.lineno} {pat}")
    assert not bad, "PROMPT carries the claim:\n" + "\n".join(bad)


def test_lexical_pin_actually_catches_an_assertion():
    asserted = "The system reads unfamiliar sets end to end.\n"
    assert list(_hits(asserted)), "pin blind to a real assertion"
    recorded = ("EARNED: it fails safe on unfamiliar sets.\n"
                "NOT EARNED:\n  It reads unfamiliar sets.\n")
    assert not list(_hits(recorded)), "pin flags a legal recording"


def test_earned_claim_is_computed_from_the_figures():
    # METRIC CHANGED SEND-127: quantity emitted, not faces derived —
    # dart emitted 1,280.53 ft² with zero faces derived.
    assert earned_claim() == CLAIM_FAILS_SAFE
    assert unattributed_lanes() == {}
    assert drafters_emitting() == 0


def test_claim_flips_only_on_more_than_one_drafter_emitting():
    one = {"tanis": {"sealed": True, "unattributed_quantity_emitted": {},
                     "attributed_quantity_emitted": {"siding_sqft": 900.0}},
           "dart": {"sealed": True, "unattributed_quantity_emitted": {},
                    "attributed_quantity_emitted": {}}}
    assert earned_claim(one) == CLAIM_FAILS_SAFE
    two = {"tanis": {"sealed": True, "unattributed_quantity_emitted": {},
                     "attributed_quantity_emitted": {"siding_sqft": 900.0}},
           "dart": {"sealed": True, "unattributed_quantity_emitted": {},
                    "attributed_quantity_emitted": {"siding_sqft": 1200.0}}}
    assert earned_claim(two) == CLAIM_READS


def test_scoreboard_shape_cannot_narrow_silently():
    for house in ("tanis", "dart"):
        assert house in FOREIGN_DRAFTER_SCOREBOARD, house
    for house, e in FOREIGN_DRAFTER_SCOREBOARD.items():
        assert set(e) == {"sealed", "unattributed_quantity_emitted",
                          "attributed_quantity_emitted"}, house
        assert isinstance(e["unattributed_quantity_emitted"], dict), house
