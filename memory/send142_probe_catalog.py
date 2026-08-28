"""SEND-142 ITEM 1 probe — READ ONLY. Names every repeated dict key in
catalog_seed.py, which value WINS today, and whether the two DIFFER.
Writes nothing."""
import ast
import pathlib
from collections import defaultdict

SRC = pathlib.Path("/app/backend/catalog_seed.py")
tree = ast.parse(SRC.read_text())


def lit(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return f"<expr {ast.unparse(node)}>"


for d in ast.walk(tree):
    if not isinstance(d, ast.Dict):
        continue
    seen = defaultdict(list)
    for k, v in zip(d.keys, d.values):
        if k is None:
            continue
        try:
            key = ast.literal_eval(k)
        except Exception:
            continue
        seen[key].append((k.lineno, v))
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    if not dupes:
        continue
    print(f"\n=== dict literal starting line {d.lineno} "
          f"({len(d.keys)} keys) ===")
    for key, occurrences in dupes.items():
        print(f"\n  KEY {key!r} — {len(occurrences)} occurrences")
        vals = []
        for ln, v in occurrences:
            val = lit(v)
            vals.append(val)
            print(f"    line {ln}: {val}")
        winner_line, winner_val = occurrences[-1]
        same = all(v == vals[-1] for v in vals)
        print(f"    WINS TODAY: line {winner_line} (last one wins)")
        print(f"    VALUES IDENTICAL: {same}")
        if not same:
            print("    *** VALUES DIFFER — STOP AND REPORT ***")
