"""SCHEMA CONSUMER KEYS — the bare-vs-underscore key class, widened
(Howard ruled 2026-08-09 send 7): "w.get('accents') against a schema
field named accent_profiles is the CONSUMER KEY BUG wearing a new coat.
WIDEN THE DETECTOR TO EVERY CONSUMER OF THE MODEL SCHEMA, not just spec
fields."

Every literal .get("key") inside the functions that consume the model's
raw extraction must name a key the prompt schema actually asks for — or
be reviewed here as an INTERNAL key our own pipeline writes. A consumer
reading a key the model is never asked to produce reads nothing,
forever, silently.

FIRST RUN OF THIS DETECTOR (2026-08-09) caught a second live instance:
_aggregate_to_hover_shape read vent_count / shutter_count (Q7 ruled
"wired on the blueprint door") while the schema never requested them —
they could only ever be 0. The schema now asks for both.

NAMED LIMIT: this scans ai_blueprint.py's consumer functions and
profile_callouts.breakdown_walls_by_profile. Consumers elsewhere join
the FNS register when they appear.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
BP = BACKEND / "routes" / "ai_blueprint.py"
PC = BACKEND / "profile_callouts.py"

# Consumer functions of the raw model dict, per file.
FNS = {
    BP: {"_enforce_evidence_or_null", "_enforce_count_column",
         "_ocr_verify_marks", "_merge_roof_pass", "_roof_pass_needed",
         "_roof_pass_sheet_indexes", "check_read_consistency",
         "build_blueprint_readback", "_aggregate_to_hover_shape",
         "_ocr_locate_evidence", "_ev_extract", "_norm_loc"},
    PC: {"breakdown_walls_by_profile"},
}

# Keys our OWN pipeline writes and reads back (never model-produced) —
# reviewed. Underscore-prefixed keys are internal by convention and
# skipped automatically; these are the reviewed bare-named internals.
INTERNAL_KEYS = {
    # readback / register / ledger row fields written by our code
    "accepted", "rejected", "carried", "cells", "code", "family",
    "field", "governed", "likely_unread", "mark", "marker", "marks",
    "read", "run", "sheet", "token", "total",
    # Keys our own pipeline writes bare-named (reviewed)
    # wall-label lookups against our own by-label dicts
    "front", "back", "left", "right",
    # locator-written precision tag on evidence srcs
    "precision",
    # profile_callouts internals (the _dormer_composition stamp's child
    # keys + the annotation-echo tag)
    "face_sqft", "cheek_sqft", "openings_deducted", "from_annotation",
}


def _schema_keys() -> set[str]:
    src = BP.read_text()
    tree = ast.parse(src)
    prompts = ""
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Name)
                        and t.id in ("SYSTEM_PROMPT", "ROOF_PASS_PROMPT")
                        and isinstance(node.value, ast.Constant)):
                    prompts += node.value.value
    return set(re.findall(r'"([a-z_][a-z0-9_]*)"\s*:', prompts))


def _consumer_gets(path: Path, fns: set[str]):
    src = path.read_text()
    tree = ast.parse(src)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and node.name in fns:
            for n in ast.walk(node):
                if (isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "get" and n.args
                        and isinstance(n.args[0], ast.Constant)
                        and isinstance(n.args[0].value, str)):
                    out.append((path.name, node.name, n.lineno,
                                n.args[0].value))
    return out


class TestSchemaConsumerKeys:
    def test_every_consumer_key_is_schema_or_reviewed_internal(self):
        schema = _schema_keys()
        assert len(schema) > 60, "schema extraction broke — investigate"
        offenders = []
        for path, fns in FNS.items():
            for fname, fn, ln, key in _consumer_gets(path, fns):
                if key.startswith("_"):
                    continue
                if key in schema or key in INTERNAL_KEYS:
                    continue
                offenders.append(f"{fname}:{ln} {fn}() reads "
                                 f".get({key!r}) — not in the model schema")
        assert not offenders, (
            "CONSUMER KEY(S) THE MODEL IS NEVER ASKED TO PRODUCE — the "
            "accents/accent_profiles class. Fix the key, add it to the "
            "schema, or review it as INTERNAL:\n" + "\n".join(offenders))

    def test_the_accents_regression_stays_dead(self):
        # The founding instance: the callout census must read the schema
        # key, never the bare near-miss.
        src = BP.read_text()
        assert 'w.get("accents")' not in src
        assert 'w.get("accent_profiles")' in src

    def test_vent_and_shutter_counts_are_in_the_schema(self):
        # Second instance, caught by this detector's first run (Q7 ruled
        # them wired on the blueprint door; the schema never asked).
        # RENAMED 2026-08-10 (Howard ruled: an ambiguous field name is a
        # defect): units and panels named so the count can't be read two
        # ways — pairs = ceil(panels ÷ 2) downstream.
        schema = _schema_keys()
        assert "vent_unit_count" in schema
        assert "shutter_panel_count" in schema
        assert "vent_count" not in schema
        assert "shutter_count" not in schema

    def test_internal_allowlist_carries_no_dead_entries(self):
        live = {key for path, fns in FNS.items()
                for _, _, _, key in _consumer_gets(path, fns)}
        schema = _schema_keys()
        dead = {k for k in INTERNAL_KEYS if k not in live or k in schema}
        assert not dead, (
            "INTERNAL_KEYS entries dead or shadowing schema keys — prune "
            "so the register stays true:\n" + "\n".join(sorted(dead)))
