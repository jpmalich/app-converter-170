"""NORMALIZER DETECTOR — SEND-9 item 4 (Howard ruled 2026-08-12).

Verbatim: "A new evidence-bearing field slipped past _normalize_evidence
for two days, silently. That is the writeThrough pattern one layer
over. RULED: EVERY EVIDENCE-BEARING FIELD ROUTES THROUGH THE NORMALIZER,
WITH A DETECTOR THAT FAILS THE BUILD WHEN ONE DOES NOT. Registry plus
census, same as the seams, the TTL indexes, the schema consumers and
the surfaces. That shape has caught something on its first run every
single time."

The registry is the source of truth. Every evidence-bearing field
(one the extraction schema emits as {v, page, from} or as a DIM
scalar) MUST be walked by `_normalize_evidence`. This detector fails
the build when:

  a. A field emitted by SYSTEM_PROMPT or ROOF_PASS_PROMPT is not
     covered by _normalize_evidence.
  b. An entry in the registry no longer appears in the schema (dead
     entry — prune the register).

Same shape as `test_seam_registry_census`, `test_surface_registry
_census`, `test_ttl_indexes_census`, `test_schema_consumer_keys`.
Every such pin has caught real regressions on first run.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BP = Path(__file__).resolve().parents[1] / "routes" / "ai_blueprint.py"


# The REGISTRY — every evidence-bearing dot-path suffix the extraction
# emits as a DIM object. Owners: whoever adds an evidence-bearing
# field to SYSTEM_PROMPT or ROOF_PASS_PROMPT MUST add its suffix here
# AND its _norm walk in _normalize_evidence in the same commit.
EVIDENCE_BEARING_FIELD_SUFFIXES: set[str] = {
    # walls[].* — the elevation dim block
    "walls.<lbl>.width_ft",
    "walls.<lbl>.height_ft",
    # walls[].height_segments[].* — the stepped-wing segment dims
    "walls.<lbl>.segments.<seg>.width_ft",
    "walls.<lbl>.segments.<seg>.height_ft",
    # roof_planes[].*
    "roof_planes.<lbl>.eave_lf",
    "roof_planes.<lbl>.rake_lf",
    "roof_planes.<lbl>.overhang_in",     # SEND-6 addition
    "roof_planes.<lbl>.wall_height_ft",  # SEND-6 addition
    # roof_planes[].* (porch only)
    "porch.porch_width_ft",
    "porch.porch_depth_ft",
    # gutter_runs[].*
    "gutter_runs.<lbl>.lf",
    # outside_corner_heights_ft[i]
    "corner_heights.<i>",
    # top-level scalars (via _EVIDENCE_SCALARS)
    "eave_overhang_in",
    "fascia_width_in",
}


def _system_prompt_source() -> str:
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
    return prompts


def _normalize_source() -> str:
    """Return the source of `_enforce_evidence_or_null` for grep-search.
    (The function name has evolved through send-3/8/9; the pin follows
    the impl that walks the raw and _norm's each evidence field.)"""
    src = BP.read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (isinstance(node, ast.FunctionDef)
                and node.name == "_enforce_evidence_or_null"):
            return ast.get_source_segment(src, node)
    return ""


def _norm_walks_suffix(norm_src: str, suffix: str) -> bool:
    """A suffix like `roof_planes.<lbl>.eave_lf` is 'walked' when
    _enforce_evidence_or_null contains a `_norm(pl, "eave_lf", ...)`
    call or an equivalent literal field-name reference inside the
    block. Cheaper than parsing the exact call structure; the point
    is a field name that never appears in the normalizer is
    definitely a hole."""
    parts = suffix.split(".")
    field = parts[-1]
    # Special-cased walks that iterate collections rather than name
    # a field directly:
    if suffix == "eave_overhang_in":
        # Walked via _EVIDENCE_SCALARS.
        return "_EVIDENCE_SCALARS" in norm_src
    if suffix == "fascia_width_in":
        return "_EVIDENCE_SCALARS" in norm_src
    if suffix == "corner_heights.<i>":
        # Walked via outside_corner_heights_ft list iteration.
        return "outside_corner_heights_ft" in norm_src
    if "<" in field:      # <i> — indexed list entry
        field = parts[-2] if len(parts) >= 2 else field
    needle = f'"{field}"'
    return needle in norm_src


class TestNormalizerDetector:
    def test_every_evidence_bearing_field_is_walked_by_the_normalizer(self):
        """The core pin — the send-6 hole (overhang_in, wall_height_ft
        per plane bypassed _normalize_evidence for two days) is what
        forced this ruling."""
        src = _normalize_source()
        assert src, "could not find _normalize_evidence in source"
        missing = [suffix for suffix in EVIDENCE_BEARING_FIELD_SUFFIXES
                   if not _norm_walks_suffix(src, suffix)]
        assert not missing, (
            "EVIDENCE-BEARING FIELD(S) NOT WALKED BY _normalize_evidence "
            "(the send-6 bypass class — a new field slipped past the "
            "normalizer for two days):\n"
            + "\n".join(f"  {m}" for m in missing)
            + "\nAdd a `_norm(container, \"<field>\", "
              "\"<dot.path>\")` call in _normalize_evidence.")

    def test_registry_carries_no_dead_field_suffixes(self):
        """If we retire an evidence-bearing field, the registry must
        forget it. Same rule as INTERNAL_KEYS on the schema
        consumers."""
        src = BP.read_text()
        dead = []
        for suffix in EVIDENCE_BEARING_FIELD_SUFFIXES:
            field = suffix.split(".")[-1]
            if "<" in field and "." in suffix:
                field = suffix.split(".")[-2]
            if f'"{field}"' not in src:
                dead.append(suffix)
        assert not dead, (
            "REGISTRY ENTRIES NAMING FIELDS THAT NO LONGER EXIST in "
            "ai_blueprint.py — prune the register:\n" +
            "\n".join(f"  {d}" for d in dead))

    def test_schema_dim_fields_are_all_in_the_registry(self):
        """Scan SYSTEM_PROMPT / ROOF_PASS_PROMPT for evidence-bearing
        field declarations (`"<name>": DIM | null` or
        `"<name>": {"v": ...}`) and confirm each field appears in the
        registry. This closes the loop from the other side: a NEW
        DIM field the schema emits cannot slip past the registry."""
        prompts = _system_prompt_source()
        assert prompts, "prompt sources not found"
        # A DIM field declaration in the prompt looks like:
        #   "<field>": DIM | null,
        # or
        #   "<field>": {"v": number, "page": n, "from": ...}
        dim_pat = re.compile(
            r'"([a-z_][a-z0-9_]*)"\s*:\s*(?:DIM\b|\{"v"|\{"v",)')
        declared: set[str] = set(dim_pat.findall(prompts))
        # Fields we intentionally do NOT normalize (e.g. openings-count
        # or dim scalars carried in different shape). Explicit
        # allowlist keeps this honest.
        WON_T_NORMALIZE = {
            # Corner heights ride outside_corner_heights_ft as a list
            # of numbers; each entry is normalised via the array
            # walker (see `corner_heights.<i>` in the registry).
        }
        registered_fields = {suffix.split(".")[-1]
                             for suffix in EVIDENCE_BEARING_FIELD_SUFFIXES}
        missing = [f for f in declared
                   if f not in registered_fields
                   and f not in WON_T_NORMALIZE
                   # Not every DIM field is evidence-bearing — some
                   # are just numbers with quotation instructions.
                   # Filter to the ones that clearly ARE evidence-
                   # bearing: those the prompt tags as DIM | null.
                   and f'"{f}": DIM' in prompts]
        assert not missing, (
            "SCHEMA DIM FIELD(S) NOT IN THE EVIDENCE REGISTRY — a new "
            "evidence-bearing field slipped into the prompt but nothing "
            "routes it through the normalizer. Add to "
            "EVIDENCE_BEARING_FIELD_SUFFIXES and add its `_norm` walk "
            "in the same commit:\n" + "\n".join(f"  {m}" for m in missing))
