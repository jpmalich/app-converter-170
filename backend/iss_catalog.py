"""ISS Siding catalog — single-tier price book sourced from Howard's
`2026_Siding_Pricing.xlsx`.

Unlike the multi-tier `catalog_seed.py` used by Vinyl / Ascend / LP Smart
estimates, ISS is single-tier with a single combined Material+Labor
price per line. The estimator UI shows one "Price" column (no separate
mat/lab split).

Each section is `(title, [(name, unit, price)])`. The serialized API
shape exposes price as the line's `mat` value so the existing
qty × price math reuses the same client-side calc helpers.
"""

ISS_SECTIONS = [
    ("Install Vinyl Siding", [
        ("Conquest",                                        "sq",   451.81),
        ("Vertical board and batten",                       "sq",   548.38),
        ("Odyssey (standard colors)",                       "sq",   478.83),
        ("Charter Oak (standard colors)",                   "sq",   504.24),
        ("Ascend Composite",                                "sq",   662.06),
        ("Prodigy (standard colors)",                       "sq",   671.43),
        ("Architectural color upcharge",                    "sq",    49.89),
        ("Tear-off",                                        "sq",    26.75),
        ("Wood shake tear off (requires a dumpster)",       "sq",   100.31),
        ("Clean up / haul away job debris",                 "job",  334.38),
        ("Dumpster",                                        "ea",   588.50),
    ]),
    ("Vinyl Soffit with Siding", [
        ("Soffit & fascia up to 13\" wide",                 "lf",    14.44),
        ("Soffit & fascia 13\"-30\" wide",                  "lf",    17.00),
        ("Fascia/rake or frieze up to 8\" coverage",        "lf",     6.13),
        ("Fascia/rake or frieze only over 8\" coverage",    "lf",     7.75),
    ]),
    ("Vinyl Soffit without Siding", [
        ("Soffit & fascia up to 13\" wide",                 "lf",    17.88),
        ("Soffit & fascia 13\"-30\" wide",                  "lf",    20.06),
        ("Fascia/rake only up to 8\" coverage",             "lf",     7.88),
        ("Fascia/rake only over 8\" coverage",              "lf",     9.56),
    ]),
    ("Porch Ceiling", [
        ("With or without siding",                          "sq ft",  7.45),
        ("Wrap porch beam",                                 "lf",    12.45),
    ]),
    ("Seamless Gutter with Siding", [
        ("Gutter",                                          "lf",    12.80),
        ("Downspout",                                       "lf",     6.18),
        ("Miters",                                          "ea",    25.00),
        ("Gutter guard (USA Shurflo)",                      "lf",     6.52),
    ]),
    ("Seamless Gutter without Siding", [
        ("Gutter",                                          "lf",    15.30),
        ("Downspout",                                       "lf",     7.20),
        ("Miters",                                          "ea",    25.00),
        ("Gutter guard (USA Shurflo)",                      "lf",     6.52),
    ]),
    ("Misc. Labor Only", [
        # Master-catalog ADOPT (Howard's ruling 2026-07-18): the sheet's
        # section organization is canonical — this REVERSES the Iter
        # 78z++++ merge. R&R lines are labor-only per the sheet.
        ("R&R gutter",                                      "lf",     4.28),
        ("R&R downspout",                                   "lf",     2.15),
    ]),
    ("Misc. Labor and Material", [
        ("Shakes and scallops",                             "sq",   889.44),
        ("Cap windows",                                     "ea",    98.44),
        ("Capping general",                                 "lf",     3.98),
        ("Cap window headers only",                         "ea",    25.76),
        ("Cap entry door",                                  "ea",   107.25),
        ("Cap patio door",                                  "ea",    99.24),
        ("Cap single garage door",                          "ea",   138.00),
        ("Build out for windows w/furring (includes capping)", "ea", 127.63),
        ("J-blocks, dryer vents",                           "ea",    48.09),
        ("Amowrap weather barrier",                         "sq",    35.99),
        ("Shutters (louvered, raised panel) standard sizes","pr",   142.78),
        ("Gable vents (square, rectangle)",                 "ea",   102.53),
        ("Gable vents (round, octagon)",                    "ea",   115.36),
        ("Fascia return",                                   "ea",    17.50),
        ("Bird box",                                        "ea",    28.75),
        ("Flashing",                                        "lf",     3.98),
    ]),
    ("Misc.", [
        # Master-catalog ADOPT (2026-07-18) — sheet keeps these in their
        # own trailing "MISC." section.
        ("Fullback in place of 1/4\" insulation",           "sq",    93.63),
        ("Replace 1x4 lumber",                              "lf",     7.15),
        ("Replace 1x6 lumber",                              "lf",     8.63),
        ("Replace 1x8 lumber",                              "lf",    10.04),
    ]),
]


# Line items Howard wants visually flagged as "common adders" — these are
# the lines a contractor most often forgets to include on an ISS quote.
# Keyed by (section title, item name) since a few names (e.g. "Gutter",
# "Downspout", "Soffit & fascia up to 13\" wide") repeat across sections
# and only one of them should carry the hint icon.
ISS_TIP_KEYS: set[tuple[str, str]] = {
    ("Install Vinyl Siding",        "Charter Oak (standard colors)"),
    ("Install Vinyl Siding",        "Architectural color upcharge"),
    ("Install Vinyl Siding",        "Tear-off"),
    ("Install Vinyl Siding",        "Clean up / haul away job debris"),
    ("Install Vinyl Siding",        "Dumpster"),
    ("Vinyl Soffit with Siding",    "Soffit & fascia up to 13\" wide"),
    ("Seamless Gutter with Siding", "Gutter"),
    ("Seamless Gutter with Siding", "Downspout"),
    ("Misc. Labor and Material",    "Cap windows"),
    ("Misc. Labor and Material",    "Cap entry door"),
    ("Misc. Labor and Material",    "J-blocks, dryer vents"),
    ("Misc. Labor and Material",    "Gable vents (square, rectangle)"),
    ("Misc. Labor and Material",    "Cap patio door"),
    ("Misc. Labor and Material",    "Cap single garage door"),
}


def build_iss_catalog() -> dict:
    """Return the API-shape catalog payload from the hardcoded seed.
    Kept synchronous for tests and seed scripts. The live API uses the
    async `load_iss_catalog()` below so supplier-admin price edits are
    honored."""
    sections = []
    for title, rows in ISS_SECTIONS:
        sections.append({
            "title": title,
            "items": [
                {
                    "name": name,
                    "unit": unit,
                    "price": price,
                    "tip": (title, name) in ISS_TIP_KEYS,
                }
                for name, unit, price in rows
            ],
        })
    return {"sections": sections}


async def ensure_iss_catalog_seeded(db) -> None:
    """Seed the `iss_catalog` collection from the hardcoded ISS_SECTIONS
    if (and only if) the collection is empty. Called on first read and
    by the admin export endpoint."""
    # Master-catalog ADOPT (Howard's ruling 2026-07-18): the sheet's
    # section organization is canonical — REVERSES the Iter 78z++++
    # merge. Re-home the six moved items and renumber orders from the
    # seed. Idempotent; runs even if the collection is already seeded.
    # Pre-heal backups: memory/backups/20260718_132744_iss_catalog_… /
    # …_estimates_iss_lines_… .
    _SPLIT_HOMES = {
        "R&R gutter": "Misc. Labor Only",
        "R&R downspout": "Misc. Labor Only",
        "Fullback in place of 1/4\" insulation": "Misc.",
        "Replace 1x4 lumber": "Misc.",
        "Replace 1x6 lumber": "Misc.",
        "Replace 1x8 lumber": "Misc.",
    }
    for name, home in _SPLIT_HOMES.items():
        await db.iss_catalog.update_many(
            {"name": name, "section": {"$ne": home}}, {"$set": {"section": home}})
        await db.estimates.update_many(
            {"lines": {"$elemMatch": {"tab": "iss", "name": name, "section": {"$ne": home}}}},
            {"$set": {"lines.$[l].section": home}},
            array_filters=[{"l.tab": "iss", "l.name": name}])
    order = {}
    for sec_idx, (title, rows) in enumerate(ISS_SECTIONS):
        for item_idx, (name, _u, _p) in enumerate(rows):
            order[(title, name)] = (sec_idx, item_idx)
    async for d in db.iss_catalog.find(
            {}, {"_id": 1, "section": 1, "name": 1, "section_order": 1, "item_order": 1}):
        so_io = order.get((d.get("section"), d.get("name")))
        if so_io and (d.get("section_order"), d.get("item_order")) != so_io:
            await db.iss_catalog.update_one(
                {"_id": d["_id"]},
                {"$set": {"section_order": so_io[0], "item_order": so_io[1]}})
    existing = await db.iss_catalog.count_documents({})
    if existing:
        return
    docs = []
    for sec_idx, (title, rows) in enumerate(ISS_SECTIONS):
        for item_idx, (name, unit, price) in enumerate(rows):
            docs.append({
                "section": title,
                "name": name,
                "unit": unit,
                "price": float(price),
                "section_order": sec_idx,
                "item_order": item_idx,
            })
    if docs:
        await db.iss_catalog.insert_many(docs)


async def load_iss_catalog(db) -> dict:
    """Build the API payload from the `iss_catalog` collection, falling
    back to the hardcoded seed on first call. Tip flags are merged in
    from `ISS_TIP_KEYS` so the highlighted-row UI keeps working even
    after admins edit prices."""
    await ensure_iss_catalog_seeded(db)
    cursor = db.iss_catalog.find({}, {"_id": 0}).sort([
        ("section_order", 1),
        ("item_order", 1),
    ])
    docs = await cursor.to_list(500)
    # Preserve the canonical section order from ISS_SECTIONS so admins
    # can't accidentally re-order sections by editing the DB.
    section_order = {title: i for i, (title, _) in enumerate(ISS_SECTIONS)}
    grouped: dict[str, list[dict]] = {}
    for d in docs:
        grouped.setdefault(d["section"], []).append(d)
    sections = []
    for title in sorted(grouped.keys(), key=lambda t: section_order.get(t, 999)):
        items = sorted(grouped[title], key=lambda x: x.get("item_order", 0))
        sections.append({
            "title": title,
            "items": [
                {
                    "name": it["name"],
                    "unit": it["unit"],
                    "price": float(it["price"]),
                    "tip": (title, it["name"]) in ISS_TIP_KEYS,
                }
                for it in items
            ],
        })
    return {"sections": sections}

