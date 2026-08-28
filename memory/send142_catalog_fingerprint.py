"""SEND-142 ITEM 1 — the catalog fingerprint. One number for every seeded
name, unit, price, tier and SKU in catalog_seed. Deduping repeated keys
must not move it by a digit."""
import hashlib
import sys


def catalog_fingerprint() -> str:
    sys.path.insert(0, "/app/backend")
    import catalog_seed as cs

    def norm(o):
        if isinstance(o, dict):
            return sorted((repr(k), norm(v)) for k, v in o.items())
        if isinstance(o, (set, frozenset)):
            return sorted(repr(x) for x in o)
        if isinstance(o, (list, tuple)):
            return [norm(x) for x in o]
        return repr(o)

    names = sorted(n for n in dir(cs) if n.isupper()
                   and isinstance(getattr(cs, n), (dict, set, list, tuple)))
    rows = []
    for n in names:
        o = getattr(cs, n)
        rows.append((n, len(o), repr(norm(o))))
    blob = "\n".join(f"{n}|{ln}|{h}" for n, ln, h in rows)
    return hashlib.sha256(blob.encode()).hexdigest(), rows


if __name__ == "__main__":
    fp, rows = catalog_fingerprint()
    for n, ln, h in rows:
        print(f"{n:28s} len={ln:4d} "
              f"{hashlib.sha256(h.encode()).hexdigest()[:16]}")
    print("\nCATALOG FINGERPRINT:", fp)
