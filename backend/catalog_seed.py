"""Seed data for the 4 price tiers from Alside's Vinyl Siding price sheet (Pittsburgh).
Material prices vary per tier; labor defaults are the same across all tiers (contractor-editable).

Tiers (cheapest → most expensive):
  - one-opp        (highest discount, top-tier accounts)
  - Builder-Dealer (builder direct accounts)
  - Contractor     (standard volume contractors)
  - whole-sale     (small / new accounts)
"""

# Section structure shared across all tiers (order + section titles)
SECTION_LAYOUT = [
    ("Install Vinyl Siding", False, [
        "Conquest .040", "Coventry .042", "Odyssey .044", "Charter Oak .046",
        "vertical board and batten", "Architectural color upcharge Vinyl",
        "Shakes and Scallops",
    ]),
    ("Ascend Cladding/Accessories", True, [
        "Ascend Composite Lap Siding", "Ascend Composite B&B (add 30% Waste)",
        'Ascend 3.5" Outside Corner — MATTE', 'Ascend 5.5" Outside Corner — MATTE',
        "Inside Corners", 'Ascend 5.5" H Channel (16\' length)',
        "Ascend J-Channel (2 per SQ of siding)",
    ]),
    ("Siding Accessories", False, [
        ".019 Coil (1 per 5 SQ Siding)", "PVC Trim Coil (1 per 5 SQ Siding)",
        "Performance G8 Trim Coil (1 per 5 SQ Siding)",
        "Outside corners", "Inside Corners (Siding)",
        '3/4" J-Channel (2 per SQ of siding)', '1/2" J-Channel (2 per SQ of siding)',
        "Finish Trim", "Starter", "House Wrap", "RainDrop", '3/8" Fan Fold',
        '2" Nails 30 lbs (1 per 15 SQ)', "Caulking (per color)",
        "J-blocks, Dryer vents", "Shutters (louvered, raised panel) standard sizes",
        "Gable vents (round, octagon)", '1 1/4" Trim Nails',
    ]),
    ("Tear-Off / Clean Up", False, [
        "Tear-Off", "Wood shake tear off (requires a dumpster)",
        "Clean up / haul away job debris", "Dumpster",
    ]),
    ("Vinyl Soffit with Siding", False, [
        'Soffit & fascia up to 13" wide — Charter Oak',
        'Soffit & fascia up to 13" wide — Greenbriar',
        'Soffit & fascia up to 13" — T2',
        'Soffit & fascia 13"–30" wide — Charter Oak',
        'Soffit & fascia 13"–30" wide — Greenbriar',
        'Soffit & fascia 13"–30" — T2',
        '3/4" J-Channel (Charter Oak)', '1/2" J-Channel (for T2 Soffit)',
        'Fascia/rake or frieze up to 8" coverage', "Cap porch band",
    ]),
    ("Porch Ceiling", False, [
        "With or without siding — Charter Oak", "Wrap porch beam",
    ]),
    ("Seamless Gutter", False, [
        'Gutter 6"', 'Downspout 6"', "Elbow", "Mitre", "Gutter Guard (USA Shurflo)",
    ]),
    ("Misc. Labor Only", False, ["R&R gutter", "R&R downspout"]),
    ("Misc. Labor & Material", False, [
        "Cap window", "Cap windows with wide crown", "Capping general",
        "Cap window headers only", "Cap entry door", "Cap patio door",
        "Cap single garage door", "Build out for windows w/ furring (includes capping)",
        "R&R Gable louvers", "Fascia Return", "Bird box", "Flashing",
    ]),
    ("Misc.", False, [
        "Cap tops of bird boxes", "Dormer upcharge", "R&R Utilities",
        "Cut out 4x4 section of wall and insulate",
    ]),
]

# Units & default labor are the same across tiers (labor defaults — contractor can override)
ITEM_META = {
    # name: (unit, lab_default)
    "Conquest .040": ("SQ", 125), "Coventry .042": ("SQ", 125), "Odyssey .044": ("SQ", 125),
    "Charter Oak .046": ("SQ", 125), "vertical board and batten": ("SQ", 125),
    "Architectural color upcharge Vinyl": ("SQ", 0), "Shakes and Scallops": ("SQ", 125),
    "Ascend Composite Lap Siding": ("SQ", 150), "Ascend Composite B&B (add 30% Waste)": ("SQ", 150),
    'Ascend 3.5" Outside Corner — MATTE': ("PCS", 0), 'Ascend 5.5" Outside Corner — MATTE': ("PCS", 0),
    "Inside Corners": ("PCS", 0), 'Ascend 5.5" H Channel (16\' length)': ("PCS", 0),
    "Ascend J-Channel (2 per SQ of siding)": ("LF", 0),
    ".019 Coil (1 per 5 SQ Siding)": ("ROLL", 0), "PVC Trim Coil (1 per 5 SQ Siding)": ("ROLL", 0),
    "Performance G8 Trim Coil (1 per 5 SQ Siding)": ("ROLL", 0),
    "Outside corners": ("PCS", 0), "Inside Corners (Siding)": ("PCS", 0),
    '3/4" J-Channel (2 per SQ of siding)': ("PCS", 0), '1/2" J-Channel (2 per SQ of siding)': ("PCS", 0),
    "Finish Trim": ("LF", 0), "Starter": ("LF", 0),
    "House Wrap": ("SQ", 2.5), "RainDrop": ("SQ", 2.5), '3/8" Fan Fold': ("SQ", 5),
    '2" Nails 30 lbs (1 per 15 SQ)': ("JOB", 0), "Caulking (per color)": ("Each", 0),
    "J-blocks, Dryer vents": ("Each", 10),
    "Shutters (louvered, raised panel) standard sizes": ("PR", 20),
    "Gable vents (round, octagon)": ("Each", 10), '1 1/4" Trim Nails': ("Box", 0),
    "Tear-Off": ("SQ", 10), "Wood shake tear off (requires a dumpster)": ("SQ", 80.25),
    "Clean up / haul away job debris": ("JOB", 150), "Dumpster": ("Each", 550),
    'Soffit & fascia up to 13" wide — Charter Oak': ("LF", 2.75),
    'Soffit & fascia up to 13" wide — Greenbriar': ("LF", 2.75),
    'Soffit & fascia up to 13" — T2': ("LF", 2.75),
    'Soffit & fascia 13"–30" wide — Charter Oak': ("LF", 3.5),
    'Soffit & fascia 13"–30" wide — Greenbriar': ("LF", 3.5),
    'Soffit & fascia 13"–30" — T2': ("LF", 3.5),
    '3/4" J-Channel (Charter Oak)': ("LF", 0), '1/2" J-Channel (for T2 Soffit)': ("LF", 0),
    'Fascia/rake or frieze up to 8" coverage': ("LF", 1.25), "Cap porch band": ("LF", 1.25),
    "With or without siding — Charter Oak": ("SQ FT", 1.25), "Wrap porch beam": ("LF", 3),
    'Gutter 6"': ("LF", 1.25), 'Downspout 6"': ("LF", 1),
    "Elbow": ("Each", 1), "Mitre": ("Each", 12), "Gutter Guard (USA Shurflo)": ("LF", 0.5),
    "R&R gutter": ("LF", 1), "R&R downspout": ("LF", 0.75),
    "Cap window": ("Each", 20), "Cap windows with wide crown": ("Each", 30),
    "Capping general": ("LF", 1), "Cap window headers only": ("Each", 8),
    "Cap entry door": ("Each", 25), "Cap patio door": ("Each", 30),
    "Cap single garage door": ("Each", 40),
    "Build out for windows w/ furring (includes capping)": ("Each", 50),
    "R&R Gable louvers": ("Each", 10), "Fascia Return": ("Each", 8),
    "Bird box": ("Each", 10), "Flashing": ("LF", 1),
    "Cap tops of bird boxes": ("Each", 1), "Dormer upcharge": ("Each", 100),
    "R&R Utilities": ("Each", 1), "Cut out 4x4 section of wall and insulate": ("Each", 50),
}

# Material prices per tier (name → mat $)
TIER_PRICES = {
    "one-opp": {
        "Conquest .040": 75.71, "Coventry .042": 81.17, "Odyssey .044": 100.11,
        "Charter Oak .046": 113.57, "vertical board and batten": 113.57,
        "Architectural color upcharge Vinyl": 15, "Shakes and Scallops": 419.94,
        "Ascend Composite Lap Siding": 309.64, "Ascend Composite B&B (add 30% Waste)": 366.96,
        'Ascend 3.5" Outside Corner — MATTE': 40.42, 'Ascend 5.5" Outside Corner — MATTE': 59.36,
        "Inside Corners": 11.83, 'Ascend 5.5" H Channel (16\' length)': 71.66,
        "Ascend J-Channel (2 per SQ of siding)": 10.4,
        ".019 Coil (1 per 5 SQ Siding)": 133.23, "PVC Trim Coil (1 per 5 SQ Siding)": 149.74,
        "Performance G8 Trim Coil (1 per 5 SQ Siding)": 145.89,
        "Outside corners": 19.69, "Inside Corners (Siding)": 9.84,
        '3/4" J-Channel (2 per SQ of siding)': 4.55, '1/2" J-Channel (2 per SQ of siding)': 4.55,
        "Finish Trim": 0.45, "Starter": 0.45,
        "House Wrap": 11.55, "RainDrop": 30.73, '3/8" Fan Fold': 11.06,
        '2" Nails 30 lbs (1 per 15 SQ)': 81.63, "Caulking (per color)": 8.23,
        "J-blocks, Dryer vents": 13.49,
        "Shutters (louvered, raised panel) standard sizes": 114.2225,
        "Gable vents (round, octagon)": 92.2875, '1 1/4" Trim Nails': 9,
        "Tear-Off": 0, "Wood shake tear off (requires a dumpster)": 0,
        "Clean up / haul away job debris": 0, "Dumpster": 0,
        'Soffit & fascia up to 13" wide — Charter Oak': 1.4,
        'Soffit & fascia up to 13" wide — Greenbriar': 1.23,
        'Soffit & fascia up to 13" — T2': 0.95,
        'Soffit & fascia 13"–30" wide — Charter Oak': 2.8,
        'Soffit & fascia 13"–30" wide — Greenbriar': 2.46,
        'Soffit & fascia 13"–30" — T2': 1.9,
        '3/4" J-Channel (Charter Oak)': 0.46, '1/2" J-Channel (for T2 Soffit)': 0.46,
        'Fascia/rake or frieze up to 8" coverage': 2.66, "Cap porch band": 2.66,
        "With or without siding — Charter Oak": 1.4, "Wrap porch beam": 2.66,
        'Gutter 6"': 3.25, 'Downspout 6"': 2.8, "Elbow": 2.69, "Mitre": 13.75,
        "Gutter Guard (USA Shurflo)": 2.25,
        "R&R gutter": 0, "R&R downspout": 0,
        "Cap window": 0, "Cap windows with wide crown": 65, "Capping general": 0,
        "Cap window headers only": 0, "Cap entry door": 0, "Cap patio door": 0,
        "Cap single garage door": 0, "Build out for windows w/ furring (includes capping)": 0,
        "R&R Gable louvers": 0, "Fascia Return": 0, "Bird box": 0, "Flashing": 0,
        "Cap tops of bird boxes": 60, "Dormer upcharge": 0, "R&R Utilities": 0,
        "Cut out 4x4 section of wall and insulate": 100,
    },
    "Builder-Dealer": {
        "Conquest .040": 92.19, "Coventry .042": 95.03, "Odyssey .044": 116.22,
        "Charter Oak .046": 125.46, "vertical board and batten": 136.56,
        "Architectural color upcharge Vinyl": 20, "Shakes and Scallops": 419.94,
        "Ascend Composite Lap Siding": 332.6, "Ascend Composite B&B (add 30% Waste)": 408.66,
        'Ascend 3.5" Outside Corner — MATTE': 40.42, 'Ascend 5.5" Outside Corner — MATTE': 59.36,
        "Inside Corners": 11.83, 'Ascend 5.5" H Channel (16\' length)': 61.05,
        "Ascend J-Channel (2 per SQ of siding)": 10.4,
        ".019 Coil (1 per 5 SQ Siding)": 161.33, "PVC Trim Coil (1 per 5 SQ Siding)": 167.08,
        "Performance G8 Trim Coil (1 per 5 SQ Siding)": 170.53,
        "Outside corners": 31.54, "Inside Corners (Siding)": 15.77,
        '3/4" J-Channel (2 per SQ of siding)': 11.52, '1/2" J-Channel (2 per SQ of siding)': 7.28,
        "Finish Trim": 7.28, "Starter": 0.45,
        "House Wrap": 11.55, "RainDrop": 30.73, '3/8" Fan Fold': 11.06,
        '2" Nails 30 lbs (1 per 15 SQ)': 81.63, "Caulking (per color)": 8.23,
        "J-blocks, Dryer vents": 13.49,
        "Shutters (louvered, raised panel) standard sizes": 114.2225,
        "Gable vents (round, octagon)": 92.2875, '1 1/4" Trim Nails': 9,
        "Tear-Off": 0, "Wood shake tear off (requires a dumpster)": 0,
        "Clean up / haul away job debris": 0, "Dumpster": 0,
        'Soffit & fascia up to 13" wide — Charter Oak': 1.82,
        'Soffit & fascia up to 13" wide — Greenbriar': 1.63,
        'Soffit & fascia up to 13" — T2': 1.38,
        'Soffit & fascia 13"–30" wide — Charter Oak': 3.64,
        'Soffit & fascia 13"–30" wide — Greenbriar': 3.26,
        'Soffit & fascia 13"–30" — T2': 2.76,
        '3/4" J-Channel (Charter Oak)': 0.53, '1/2" J-Channel (for T2 Soffit)': 0.53,
        'Fascia/rake or frieze up to 8" coverage': 0, "Cap porch band": 0,
        "With or without siding — Charter Oak": 1.82, "Wrap porch beam": 3.22,
        'Gutter 6"': 3.25, 'Downspout 6"': 2.8, "Elbow": 2.69, "Mitre": 13.75,
        "Gutter Guard (USA Shurflo)": 2.25,
        "R&R gutter": 0, "R&R downspout": 0,
        "Cap window": 0, "Cap windows with wide crown": 65, "Capping general": 0,
        "Cap window headers only": 0, "Cap entry door": 0, "Cap patio door": 0,
        "Cap single garage door": 0, "Build out for windows w/ furring (includes capping)": 0,
        "R&R Gable louvers": 0, "Fascia Return": 0, "Bird box": 0, "Flashing": 0,
        "Cap tops of bird boxes": 60, "Dormer upcharge": 0, "R&R Utilities": 0,
        "Cut out 4x4 section of wall and insulate": 100,
    },
    "Contractor": {
        "Conquest .040": 97.04, "Coventry .042": 100.03, "Odyssey .044": 116.22,
        "Charter Oak .046": 136.22, "vertical board and batten": 143.74,
        "Architectural color upcharge Vinyl": 23, "Shakes and Scallops": 419.94,
        "Ascend Composite Lap Siding": 332.6, "Ascend Composite B&B (add 30% Waste)": 408.66,
        'Ascend 3.5" Outside Corner — MATTE': 40.42, 'Ascend 5.5" Outside Corner — MATTE': 59.36,
        "Inside Corners": 11.83, 'Ascend 5.5" H Channel (16\' length)': 71.66,
        "Ascend J-Channel (2 per SQ of siding)": 10.4,
        ".019 Coil (1 per 5 SQ Siding)": 161.33, "PVC Trim Coil (1 per 5 SQ Siding)": 167.08,
        "Performance G8 Trim Coil (1 per 5 SQ Siding)": 170.53,
        "Outside corners": 31.54, "Inside Corners (Siding)": 15.77,
        '3/4" J-Channel (2 per SQ of siding)': 11.52, '1/2" J-Channel (2 per SQ of siding)': 7.28,
        "Finish Trim": 7.28, "Starter": 0.45,
        "House Wrap": 11.55, "RainDrop": 30.73, '3/8" Fan Fold': 11.06,
        '2" Nails 30 lbs (1 per 15 SQ)': 81.63, "Caulking (per color)": 8.23,
        "J-blocks, Dryer vents": 13.49,
        "Shutters (louvered, raised panel) standard sizes": 114.2225,
        "Gable vents (round, octagon)": 92.2875, '1 1/4" Trim Nails': 9,
        "Tear-Off": 0, "Wood shake tear off (requires a dumpster)": 0,
        "Clean up / haul away job debris": 0, "Dumpster": 0,
        'Soffit & fascia up to 13" wide — Charter Oak': 2.02,
        'Soffit & fascia up to 13" wide — Greenbriar': 1.8,
        'Soffit & fascia up to 13" — T2': 1.38,
        'Soffit & fascia 13"–30" wide — Charter Oak': 3.64,
        'Soffit & fascia 13"–30" wide — Greenbriar': 3.24,
        'Soffit & fascia 13"–30" — T2': 2.76,
        '3/4" J-Channel (Charter Oak)': 1.15, '1/2" J-Channel (for T2 Soffit)': 0.72,
        'Fascia/rake or frieze up to 8" coverage': 2.94, "Cap porch band": 2.94,
        "With or without siding — Charter Oak": 2.02, "Wrap porch beam": 3.22,
        'Gutter 6"': 3.25, 'Downspout 6"': 2.8, "Elbow": 2.69, "Mitre": 13.75,
        "Gutter Guard (USA Shurflo)": 2.25,
        "R&R gutter": 0, "R&R downspout": 0,
        "Cap window": 0, "Cap windows with wide crown": 65, "Capping general": 0,
        "Cap window headers only": 0, "Cap entry door": 0, "Cap patio door": 0,
        "Cap single garage door": 0, "Build out for windows w/ furring (includes capping)": 0,
        "R&R Gable louvers": 0, "Fascia Return": 0, "Bird box": 0, "Flashing": 0,
        "Cap tops of bird boxes": 60, "Dormer upcharge": 0, "R&R Utilities": 0,
        "Cut out 4x4 section of wall and insulate": 100,
    },
    "whole-sale": {
        "Conquest .040": 102.15, "Coventry .042": 105.3, "Odyssey .044": 122.34,
        "Charter Oak .046": 151.31, "vertical board and batten": 151.31,
        "Architectural color upcharge Vinyl": 23, "Shakes and Scallops": 419.94,
        "Ascend Composite Lap Siding": 332.6, "Ascend Composite B&B (add 30% Waste)": 408.66,
        'Ascend 3.5" Outside Corner — MATTE': 40.42, 'Ascend 5.5" Outside Corner — MATTE': 59.36,
        "Inside Corners": 11.83, 'Ascend 5.5" H Channel (16\' length)': 71.66,
        "Ascend J-Channel (2 per SQ of siding)": 10.4,
        ".019 Coil (1 per 5 SQ Siding)": 161.33, "PVC Trim Coil (1 per 5 SQ Siding)": 167.08,
        "Performance G8 Trim Coil (1 per 5 SQ Siding)": 170.53,
        "Outside corners": 25.81, "Inside Corners (Siding)": 12.9,
        '3/4" J-Channel (2 per SQ of siding)': 5.23, '1/2" J-Channel (2 per SQ of siding)': 5.23,
        "Finish Trim": 5.95, "Starter": 0.45,
        "House Wrap": 11.55, "RainDrop": 30.73, '3/8" Fan Fold': 11.06,
        '2" Nails 30 lbs (1 per 15 SQ)': 81.63, "Caulking (per color)": 8.23,
        "J-blocks, Dryer vents": 13.49,
        "Shutters (louvered, raised panel) standard sizes": 114.2225,
        "Gable vents (round, octagon)": 92.2875, '1 1/4" Trim Nails': 9,
        "Tear-Off": 0, "Wood shake tear off (requires a dumpster)": 0,
        "Clean up / haul away job debris": 0, "Dumpster": 0,
        'Soffit & fascia up to 13" wide — Charter Oak': 2.02,
        'Soffit & fascia up to 13" wide — Greenbriar': 1.8,
        'Soffit & fascia up to 13" — T2': 1.38,
        'Soffit & fascia 13"–30" wide — Charter Oak': 3.64,
        'Soffit & fascia 13"–30" wide — Greenbriar': 3.24,
        'Soffit & fascia 13"–30" — T2': 2.76,
        '3/4" J-Channel (Charter Oak)': 1.15, '1/2" J-Channel (for T2 Soffit)': 0.72,
        'Fascia/rake or frieze up to 8" coverage': 2.94, "Cap porch band": 2.94,
        "With or without siding — Charter Oak": 2.02, "Wrap porch beam": 3.22,
        'Gutter 6"': 3.25, 'Downspout 6"': 2.8, "Elbow": 2.69, "Mitre": 13.75,
        "Gutter Guard (USA Shurflo)": 2.25,
        "R&R gutter": 0, "R&R downspout": 0,
        "Cap window": 0, "Cap windows with wide crown": 65, "Capping general": 0,
        "Cap window headers only": 0, "Cap entry door": 0, "Cap patio door": 0,
        "Cap single garage door": 0, "Build out for windows w/ furring (includes capping)": 0,
        "R&R Gable louvers": 0, "Fascia Return": 0, "Bird box": 0, "Flashing": 0,
        "Cap tops of bird boxes": 60, "Dormer upcharge": 0, "R&R Utilities": 0,
        "Cut out 4x4 section of wall and insulate": 100,
    },
}


def build_tier_sections(tier_name: str) -> list:
    """Build the full sections list for a given tier name using SECTION_LAYOUT + TIER_PRICES."""
    prices = TIER_PRICES[tier_name]
    out = []
    for title, ascend, item_names in SECTION_LAYOUT:
        items = []
        for n in item_names:
            unit, lab = ITEM_META.get(n, ("Each", 0))
            items.append({
                "name": n, "unit": unit,
                "mat": float(prices.get(n, 0)),
                "lab": float(lab),  # labor default — contractor can override
            })
        out.append({"title": title, "ascend": ascend, "items": items})
    return out


# Default tier for new companies (cheapest = safest first impression)
DEFAULT_TIER_NAME = "one-opp"

# Legacy export — keeps backward compat with any code that still reads DEFAULT_SECTIONS
DEFAULT_SECTIONS = build_tier_sections(DEFAULT_TIER_NAME)

# All tier names, in display order
TIER_NAMES = ["one-opp", "Builder-Dealer", "Contractor", "whole-sale"]
