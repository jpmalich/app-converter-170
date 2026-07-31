// Catalog item / section / unit translations.
// Brand-name products (Conquest, Coventry, Odyssey, Charter Oak, Greenbriar, T2,
// Ascend) stay in English — they're product names, not descriptions. Generic
// service descriptions and section titles do get translated.
//
// Catalog data lives in the backend in English; these maps translate at render
// time. If a key isn't here, we fall back to the original (English) string.

const SECTIONS_ES = {
  "Install Vinyl Siding": "Vinil",
  "Vinyl Siding": "Vinil",
  "Ascend Cladding": "Revestimiento Ascend",
  "Ascend Cladding/Accessories": "Revestimiento Ascend / Accesorios",
  "Siding Accessories": "Accesorios de vinil",
  "Tear-Off / Clean Up": "Demolición / Limpieza",
  "Vinyl Soffit with Siding": "Plafón de vinil con vinil",
  "Porch Ceiling": "Techo de Porche",
  "Seamless Gutter": "Canalón sin uniones",
  "Misc. Labor Only": "Mano de obra (varios)",
  "Misc. Labor & Material": "Mano de obra y material (varios)",
  "Misc.": "Varios",
  // Iter 38–40: window catalog sections (shared by Vero + Mezzo tabs)
  "Window Installation": "Instalación de ventanas",
  "Sliding Glass Door Install": "Instalación de puerta corrediza",
  "Window Material List": "Lista de materiales · ventanas",
  "Window Exterior Trim Work": "Moldura exterior · ventanas",
  "Window Interior Trim Work": "Moldura interior · ventanas",
  "Window Misc.": "Ventanas · varios",
  // Vero W×H product panels (rendered via VeroPanel's section-tag)
  "Vero Double Hung": "Vero Doble Colgante",
  "Vero 2-Lite Slider": "Vero Corrediza 2 hojas",
  "Vero 3-Lite Slider": "Vero Corrediza 3 hojas",
  "Vero Picture": "Vero Fija (Picture)",
  "Vero Patio Door": "Vero Puerta de Patio",
  "Vero 1-Lite Casement": "Vero Batiente 1 hoja",
  // Mezzo W×H product panels
  "Mezzo Double Hung": "Mezzo Doble Colgante",
  "Mezzo 2-Lite Slider": "Mezzo Corrediza 2 hojas",
  "Mezzo 3-Lite Slider": "Mezzo Corrediza 3 hojas",
  "Mezzo Picture": "Mezzo Fija (Picture)",
};

// Catalog item translations. Only translate generic descriptions; leave product
// model numbers and brand-name profiles alone.
// ITEMS_ES RETIRED (Howard ruled 2026-07-31): catalog item / SKU names
// render VERBATIM in every language. Spanish help lives in
// itemDescriptions.js (secondary text), never on the name.

// Unit abbreviations. Construction trades in the US often keep English shorthand
// even in Spanish work orders, but a few have clear translations.
const UNITS_ES = {
  "SQ": "MC",       // square (100 sq ft) → metro cuadrado conceptually; keep "MC" abbreviation
  "LF": "PL",       // linear foot → pie lineal
  "PCS": "PZA",     // pieces → piezas
  "Each": "C/U",    // each → cada uno
  "each": "C/U",
  "EA": "C/U",
  "JOB": "TRAB",    // job → trabajo
  "ROLL": "ROLLO",
  "PR": "PAR",      // pair → par
  "Box": "CAJA",
  "SQ FT": "PIE²",
  "ADD": "REC",     // surcharge / adder
};

export function tSection(name, lang) {
  if (lang !== "es") return name;
  return SECTIONS_ES[name] || name;
}

// Iter 57cc — Legacy item-name aliases. Whenever a catalog item gets
// renamed, drop an entry here so old estimates' saved `lines[].name`
// (e.g. "RainDrop House Wrap") render under the new label ("RainDrop")
// without a destructive DB migration. New estimates always store the
// new name; this map only kicks in when a stored name is no longer
// in the catalog.
const ITEM_NAME_ALIASES = {
  // Iter 79 (Feb 2026): supplier-spec renames — show OLD line names
  // under the NEW catalog label so historical quotes don't show a
  // mismatched/orphaned row name. The DB migration in services.py
  // rewrites lines[].name on the next boot, but this alias keeps the
  // UI consistent in the transient window before the migration runs
  // OR if an old serialized estimate sneaks through.
  "RainDrop House Wrap": "RainDrop",
  ".019 Coil (1 per 5 Sq Siding)": ".019 Coil",
  "Charter Oak Soffit Standard color": "Soffit & fascia Charter Oak Standard Color",
  "Charter Oak Soffit Architectural color": "Soffit & fascia Charter Oak Architectural color",
  "Greenbriar Soffit": "Soffit & fascia Greenbriar",
  "T2 Soffit": "Soffit & fascia 2T",
  '1/2" Soffit J-Channel (for T2 Soffit)': '1/2" J-Channel White',
  "With or without siding Charter Oak": "Charter Oak Soffit White",
};

export function canonicalItemName(name) {
  return ITEM_NAME_ALIASES[name] || name;
}

export function tItem(name, lang) {
  // SKU NAMES NEVER TRANSLATE (Howard ruled 2026-07-31): the product name
  // is the SAME string in every language — labels, headings and
  // descriptors around it translate; the name itself never does. This is
  // what protects price binding from the second language. Legacy-alias
  // canonicalization stays (identity healing, not translation).
  return ITEM_NAME_ALIASES[name] || name;
}

export function tUnit(unit, lang) {
  if (lang !== "es") return unit;
  return UNITS_ES[unit] || unit;
}

// ───────────────────────── Color translations ─────────────────────────
// Covers both the Vero + Mezzo factory finishes as well as the per-window
// "sister color" combos shown on the Vero W×H panel (e.g. "White Interior
// / White Exterior"). Keys mirror the strings in `lib/colorOptions.js`
// and `vero_seed_prices.json` exactly so a single `tColor()` call resolves
// every dropdown option site-wide.
const COLORS_ES = {
  // Extruded solids (shared by Vero + Mezzo)
  "White": "Blanco",
  "Beige": "Beige",
  "Classic Clay": "Arcilla clásica",
  "Tan": "Tostado",

  // Mezzo FrameWorks Finishes (exterior)
  "Black Laminate": "Laminado negro",
  "Brown Laminate": "Laminado café",
  "Architectural Bronze": "Bronce arquitectónico",
  "American Terra": "Terra americano",
  "Hudson Khaki": "Caqui Hudson",
  "Desert Clay": "Arcilla del desierto",
  "Sand Dune": "Duna de arena",
  "English Red": "Rojo inglés",
  "Forest Green": "Verde bosque",
  "Silver": "Plateado",
  "Castle Gray": "Gris castillo",

  // Mezzo Woodgrain Laminate (interior)
  "White Woodgrain": "Veteado blanco",
  "Rich Maple": "Arce intenso",
  "Light Oak": "Roble claro",
  "Dark Oak": "Roble oscuro",
  "Foxwood": "Foxwood",
  "Cherry": "Cerezo",

  // Vero interior laminate woodgrains
  "Cavalier Oak": "Roble Cavalier",
  "Colonial Cherry": "Cerezo Colonial",

  // Vero painted finishes (already disambiguated with " (Paint)" suffix)
  "White (Paint)": "Blanco (pintura)",
  "Black (Paint)": "Negro (pintura)",
  "Tan (Paint)": "Tostado (pintura)",
  "Graphite": "Grafito",
  "Sterling": "Plata Sterling",
  "Forest": "Bosque",
  "Bronze": "Bronce",
  "Royal Brown": "Café real",
  "Terra": "Terra",
  "Pebble": "Guijarro",
  "Cream": "Crema",

  // Vero sister-color combos (W×H per-opening picker)
  "White Interior/White Exterior": "Blanco interior / Blanco exterior",
  "Tan Interior/Tan Exterior": "Tostado interior / Tostado exterior",
  "White Interior/Laminate Exterior": "Blanco interior / Laminado exterior",
  "Laminate Interior/White Exterior": "Laminado interior / Blanco exterior",
  "Woodgrain Interior/White Exterior": "Veteado interior / Blanco exterior",
  "Wood Interior/White Exterior": "Madera interior / Blanco exterior",
};

// Optgroup labels used inside the color <select>s
const COLOR_GROUP_LABELS_ES = {
  "Extruded Solid": "Sólido extruido",
  "FrameWorks Finish": "Acabado FrameWorks",
  "Woodgrain Laminate": "Laminado veteado",
  "Extruded Vinyl (color through)": "Vinil extruido (color en toda la pieza)",
  "Laminate · white base only": "Laminado · solo sobre base blanca",
  "Painted Finish": "Acabado pintado",
  "Laminate Woodgrain · white base only": "Laminado veteado · solo sobre base blanca",
};

export function tColor(name, lang) {
  if (lang !== "es" || !name) return name || "";
  return COLORS_ES[name] || name;
}

export function tColorGroup(label, lang) {
  if (lang !== "es" || !label) return label || "";
  return COLOR_GROUP_LABELS_ES[label] || label;
}
