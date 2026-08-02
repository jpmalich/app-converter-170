"""All Pydantic request/response models live here."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    company_name: Optional[str] = None
    invite_code: Optional[str] = None
    signup_code: Optional[str] = None  # required to create a new company


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class CatalogItem(BaseModel):
    name: str
    unit: str
    mat: float
    lab: float
    ami_part: Optional[str] = None  # Supplier SKU for the material list / ordering
    # PRICE AGE (ruled 2026-07-31): stamped server-side on every human
    # price write; seed syncs never stamp. Optional so old docs load.
    price_changed_at: Optional[str] = None
    price_changed_by: Optional[str] = None


class CatalogSection(BaseModel):
    title: str
    ascend: bool = False
    # Which tab(s) this section belongs to in the multi-product estimator.
    # Values: "vinyl" | "ascend" | "lp_smart". Sections shared between
    # product lines (e.g. Siding Accessories, Soffit, Gutter, Tear-Off,
    # Misc Labor) appear in multiple tabs.
    product_lines: List[str] = ["vinyl", "ascend"]
    items: List[CatalogItem]


class CatalogOverridesIn(BaseModel):
    overrides: dict  # { "<section>::<name>": {"lab"?: float} }


class TierUpdate(BaseModel):
    name: Optional[str] = None
    sections: Optional[List[CatalogSection]] = None
    # TRANSPOSITION GATE (ruled 2026-07-31): required True when any edited
    # price moves past the ×3 threshold — the editor gets a 409 naming the
    # rows and re-sends after the human confirms.
    confirm_magnitude: bool = False


class CompanyTierAssign(BaseModel):
    price_tier_id: str


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None  # set "" or None to clear
    quote_footer_enabled: Optional[bool] = None


class BrandingUpdate(BaseModel):
    supplier_name: Optional[str] = None
    supplier_tagline: Optional[str] = None
    supplier_logo_url: Optional[str] = None
    default_pricing_mode: Optional[str] = None
    # PRICE AGE (ruled 2026-07-31): rows whose price is older than this
    # threshold get the stale chip on the admin surfaces.
    stale_price_days: Optional[int] = None


class InviteContractorIn(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    app_url: Optional[str] = None  # Frontend origin (e.g. https://app.pro-quotes.com)
    personal_note: Optional[str] = None  # Optional message from supplier admin


class EstimateLineAdder(BaseModel):
    """Per-line upgrade adder (windows only currently). When set on a
    line, its mat/lab is multiplied by the adder's own qty (NOT line.qty)
    and added to the line's subtotal — lets a 10-window line have only
    3 windows with Tempered glass + 4 windows with Grid Pattern, etc.
    See services.calc_totals for the math."""
    name: str
    mat: float = 0
    lab: float = 0
    qty: float = 0


class EstimateLine(BaseModel):
    # PRESERVE DERIVATION FIELDS THROUGH EVERY WRITE (sealed 2026-07-29):
    # the strict whitelist was silently STRIPPING `note`, `_waste_included`,
    # `base_item`, `qty_pending` from every line on every API write
    # (create/PUT) — the browser autosave then destroyed the waste flags
    # and notes the derivations wrote ("suite green, broken in the
    # browser"). Extra fields now round-trip verbatim.
    model_config = ConfigDict(extra="allow")

    section: str
    name: str
    unit: str
    qty: float = 0
    mat: float = 0
    lab: float = 0
    # Iter 78 (Howard's "1C · 2C · 3A"): when an estimate imports a HOVER
    # or Blueprint takeoff, cut-prone items (siding panels, soffit
    # panels, J-channel, finish trim, corners, starter) have the
    # contractor's waste % baked into `qty` directly. The original raw
    # measurement is preserved here so future waste-% changes can
    # recompute qty without re-running the import. Lines entered
    # manually leave this field as None.
    raw_qty: Optional[float] = None
    # "yours: X · derived: Y" (Howard ruled 2026-07-31): when a human-typed
    # qty survives a re-derive, the freshly derived value is stamped here so
    # the UI can show both numbers. Never overwrites qty.
    derived_qty: Optional[float] = None
    # PROFILE OWNS ITS FAMILY (ruled 2026-07-24): "human" marks a
    # hand-typed quantity — it survives profile rebuilds/restores verbatim.
    # Derived quantities leave this None and are owned by the derivation.
    qty_src: Optional[str] = None
    # "human" = contractor-edited labor (wins forever) · "company" =
    # contractor's standing rate (companies.labor_rates / Price Catalog
    # LABOR override) · "pending" = $0 in the visible "contractor sets
    # labor" state (v3 zeroing, sealed 2026-07-24 — the provisional
    # guesses retired entirely; labor is the contractor's).
    lab_src: Optional[str] = None
    # ID BINDING (Howard ruled 2026-07-31): the app-minted catalog
    # identity (catalog_ids.py). Names/AMI are metadata; this is what
    # binds. Stamped by migration, additive-only — never derived.
    item_id: Optional[str] = None
    # BLIND-ROW NOTES (Howard ruled 2026-07-31): contractor-typed note on
    # any line — the ONLY annotation mechanism the ~39 hand-filled manual
    # rows have (they are never emitted, so no derivation note can reach
    # them). HUMAN-OWNED: survives every re-derive; prints on the
    # material list under the row. Declared (not extra="allow") so the
    # silent-strip class can never eat it.
    contractor_note: Optional[str] = Field(default=None, max_length=500)
    ami_part: Optional[str] = None  # Snapshotted at quote time so re-runs are reproducible
    # Which "tab" (product-line option) in the estimator this line belongs to.
    # "vinyl" (default — backward compat), "ascend", "lp_smart", or "windows".
    # Lets one estimate carry parallel option sets — e.g. Vinyl vs.
    # Ascend vs. LP Smart Siding — so the homeowner can compare them on
    # one quote.
    tab: str = "vinyl"
    # Iter 36: selected per-line adders (windows-tab only currently).
    # Stored as a list rather than a flag-per-adder dict so new adders
    # added to the catalog don't require an estimate-schema migration.
    adders: List[EstimateLineAdder] = []


class MiscLine(BaseModel):
    desc: str = ""
    mat: float = 0
    lab: float = 0
    tab: str = "vinyl"  # same tab semantics as EstimateLine
    # Optional section anchor — empty string means the row appears under
    # the default Misc. Labor & Material / Misc. Labor Only sections
    # (back-compat). When set (e.g. "Window Installation"), the row
    # appears inline under that catalog section as an "Add custom line"
    # entry. Lets contractors bill freeform mat+lab inside any whitelisted
    # section without polluting the Misc. catch-all.
    section: str = ""


class PorchCeiling(BaseModel):
    """A single porch ceiling — dimensional input (length × width).
    Iter 78aj (2026-02-28). Multiple porches can be added per estimate
    (front porch, back porch, side entry, etc.). Total porch ceiling
    sqft = sum(length_ft × width_ft) and is rolled into the soffit qty
    formulas alongside the eave/rake overhang contribution.
    """
    label: str = ""          # optional, e.g. "Front Porch", "Side Entry"
    length_ft: float = 0     # along the house
    width_ft: float = 0      # out from the house


class EstimateIn(BaseModel):
    customer_name: str = ""
    address: str = ""
    estimate_number: str = ""
    estimate_date: str = ""
    estimator: str = ""
    notes: str = ""
    # Iter 98 — LP component-group color selections (Material List tab).
    # {"all": name} or {group: name}; names validated against the LP
    # palette by the package endpoint, stored verbatim here.
    lp_colors: Optional[dict] = None
    # Iter 79j.47 — Customer contact + company + billing + lead source.
    # Every new field is Optional[str] with default None (NOT ""); the
    # PUT handler's model_dump(exclude_none=True) means a partial payload
    # from any client (JobInfoPanel, ISS editor, QuoteModal write-back)
    # never clobbers stored values.
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None            # cell / primary
    customer_phone_alt: Optional[str] = None        # landline / secondary
    customer_fax: Optional[str] = None
    customer_contact_method: Optional[str] = None   # cell|landline|email|text|""
    customer_company: Optional[str] = None
    customer_contact_title: Optional[str] = None
    # Empty string means "same as job address" — no separate boolean flag.
    billing_address: Optional[str] = None
    lead_source: Optional[str] = None               # referral|repeat_customer|web|...
    lead_source_detail: Optional[str] = None
    # Structured job-address parts. The composed single-line `address`
    # string above stays canonical (quote docs, CSVs, geocoding all
    # read that field). These parts drive the 4-field UI grid and are
    # persisted verbatim so a subsequent PUT payload without them
    # doesn't lose them.
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None
    # Structured billing-address parts (only populated when the "same
    # as job address" checkbox is un-checked).
    billing_street: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_zip: Optional[str] = None
    # Estimate-level color choices (one per material family). Print on the
    # material list so the supplier knows exactly which colors to pull.
    siding_color: str = ""
    ascend_color: str = ""
    # Pelican Bay shake palette (Iter 52) — separate field for shake
    # accents on gables/dormers via the "Quote gables as shake" toggle.
    shake_color: str = ""
    # Board & Batten accent color (Iter 52).
    board_batten_color: str = ""
    accessories_color: str = ""
    outside_corner_color: str = ""
    soffit_fascia_color: str = ""
    window_wrap_color: str = ""
    # Aluminum gutter/downspout color — separate field since gutter coil
    # ships in its own palette (aluminum coil colors, not vinyl).
    gutter_color: str = ""
    # Window product colors (Windows tab) — appear on the material list so
    # the installer pulls the right Vero color stock for frames + interior
    # + exterior trim. The original `window_*_color` fields are the Vero
    # palette; `mezzo_*_color` are added in Iter 38 for the Mezzo line.
    window_frame_color: str = ""
    window_interior_color: str = ""
    window_exterior_color: str = ""
    mezzo_interior_color: str = ""
    mezzo_exterior_color: str = ""
    waste_pct: float = 0
    # SHAKE REVEAL (register #4 ruled 2026-07-28): contractor-selectable,
    # bounded 7"–10", default 7" — per LP install instructions ("540
    # Series Trim is recommended when the shake reveal selected ranges
    # between a maximum of 10 inches to a minimum of 7 inches").
    # Optional so partial PUTs never clobber; None = the ruled 7" default.
    shake_reveal_in: Optional[float] = None

    # TRADE SPECS (Howard ruled 2026-07-29): the contractor telling the
    # app what he is installing — never a check. Optional so partial PUTs
    # never clobber; None = the ruled defaults (12" o.c. / 8" fascia).
    batten_spacing_in: Optional[int] = None
    fascia_width_in: Optional[int] = None
    # PANEL SIZE + WRAP TRIM WIDTH (Howard ruled 2026-07-30): panel size
    # changes COUNT and SKU (4×10 = 40 ft², 4×8 = 32 ft²); wrap-trim width
    # changes ONLY the 540 SKU name. Declared here so the PUT can never
    # silent-strip them (F2 class).
    panel_size: Optional[str] = None
    wrap_trim_width_in: Optional[int] = None
    # PHOTO FILL-IN BOXES (Howard ruled 2026-08-01, Three Doors step 6):
    # four, PHOTO DOOR ONLY — the photo genuinely cannot see them.
    # Declared here so the PUT can never silent-strip them (F2 class).
    # A box only FILLS a hole in a photo-sourced blob; the fold
    # (measure_staging.fold_photo_fillins) is inert on hover/blueprint.
    photo_soffit_sqft: Optional[float] = None
    photo_drip_edge_lf: Optional[float] = None
    photo_total_trim_sqft: Optional[float] = None
    photo_frieze_present: Optional[bool] = None

    @field_validator("photo_soffit_sqft", "photo_drip_edge_lf",
                     "photo_total_trim_sqft")
    @classmethod
    def _photo_fillin_non_negative(cls, v):
        if v is None:
            return v
        if float(v) < 0:
            raise ValueError("photo fill-in values cannot be negative "
                             "(Three Doors step 6, ruled 2026-08-01)")
        return float(v)

    @field_validator("panel_size")
    @classmethod
    def _panel_size_valid(cls, v):
        if v is None:
            return v
        if str(v) not in ("4x10", "4x8"):
            raise ValueError('panel size must be "4x10" or "4x8" '
                             "(38 Series panels — ruled 2026-07-30)")
        return str(v)

    @field_validator("wrap_trim_width_in")
    @classmethod
    def _wrap_trim_width_valid(cls, v):
        if v is None:
            return v
        if int(v) not in (4, 6, 8, 10, 12):
            raise ValueError("wrap trim width must be 4, 6, 8, 10 or 12 inches "
                             "(540 Series widths — ruled 2026-07-30)")
        return int(v)

    @field_validator("batten_spacing_in")
    @classmethod
    def _batten_spacing_valid(cls, v):
        if v is None:
            return v
        if int(v) not in (12, 16, 24):
            raise ValueError('batten spacing must be 12, 16 or 24 (o.c.) — '
                             '8" retired (ruled 2026-07-29)')
        return int(v)

    @field_validator("fascia_width_in")
    @classmethod
    def _fascia_width_valid(cls, v):
        if v is None:
            return v
        if int(v) not in (4, 6, 8, 10, 12):
            raise ValueError("fascia width must be 4, 6, 8, 10 or 12 inches "
                             "(440 Series widths — ruled 2026-07-29)")
        return int(v)

    @field_validator("shake_reveal_in")
    @classmethod
    def _shake_reveal_bounds(cls, v):
        if v is None:
            return v
        if not (7.0 <= float(v) <= 10.0):
            raise ValueError(
                'shake reveal must be between 7" and 10" — LP install '
                "instructions (register #4 ruled 2026-07-28)")
        return float(v)

    # Q8 (ruled 2026-07-27): per-estimate color-tier selector — "standard"
    # (default) or "architectural"; re-lands vinyl/ascend derivations on
    # the Architectural-color catalog twins. Manual swap stays for one-offs.
    color_tier: str = "standard"
    # Iter 78 — LP SmartSide soffit steering. Controls how the
    # auto-imported soffit qty is split between Vented (eaves) and
    # Closed (rakes) on LP estimates only. Backend's HOVER spec
    # splits by surface; this lets the contractor override:
    #   "mix"    — default, vented on eaves + closed on rakes (current)
    #   "vented" — 100% vented (collapse closed qty into vented)
    #   "closed" — 100% closed (collapse vented qty into closed)
    lp_soffit_type: str = "mix"
    tax_enabled: bool = True
    tax_rate: float = 7.0
    margin_pct: float = 30.0
    pricing_mode: Optional[str] = None  # "margin" | "markup"; falls back to supplier default
    # Estimate kind — controls which workspace the estimate belongs to.
    # "siding" (default, back-compat for existing estimates) shows in the
    # siding dashboard with all siding tabs visible; "windows" shows in the
    # dedicated windows dashboard with only the Windows tab visible.
    kind: str = "siding"
    # Iter 36 (windows-kind only): install method drives which install
    # line ("Window DH/Slider - Pocket Install" vs Full Fin vs Block
    # Frame) gets the auto-synced qty. Empty string = contractor manually
    # picks the install row.
    install_method: str = ""
    # Iter 36 (windows-kind only): true when the home was built before
    # 1978 and Lead-Safe RRP is required. Auto-fills Lead Safe Test Fee
    # (qty=1) + Lead Safe Installation Practices (qty=total window count).
    home_pre_1978: bool = False
    # Iter 41: cross-kind pairing. When a contractor uploads a HOVER on a
    # siding estimate that contains windows data (or vice versa), the
    # importer auto-spawns a paired estimate of the opposite kind so the
    # window scope doesn't get stranded on a siding quote. Both estimates
    # store the other's id here so the editor + dashboard can render a
    # chain-link badge linking them. One-time copy on creation — they're
    # independent docs after that.
    paired_estimate_id: Optional[str] = None
    # Iter 74 (2026-06-22): LP got its own workspace (Iter 73). When a
    # contractor quotes both siding + LP for the same house, the "Pair to
    # LP" button copies customer/address/HOVER measurements into a new
    # lp_smart-kind estimate and back-points here. Independent of the
    # siding↔windows pairing above so a single siding draft can fan out
    # to BOTH a windows-pair and an LP-pair.
    paired_lp_estimate_id: Optional[str] = None
    lines: List[EstimateLine] = []
    misc_labor: List[MiscLine] = []
    misc_material: List[MiscLine] = []
    # Iter 37: Mezzo W×H-driven openings. Each entry is one quoted
    # opening (a single window on the customer's home). Lives in its
    # own list rather than under `lines` because the data shape is
    # different (W/H drive the price via bucket lookup; adder prices
    # depend on size). See routes/mezzo.py for catalog lookup.
    mezzo_openings: List["MezzoOpening"] = []
    # Iter 39: Vero W×H-driven openings (Phase 4). Same shape as Mezzo
    # but adds a `sister_color` selector + `glass_package` + optional
    # `tempered_upcharge` + `premium_options[]`. Patio Door variant uses
    # `model` instead of width/height.
    vero_openings: List["VeroOpening"] = []
    # Iter 57v — Window Package Quote override. When `enabled` and
    # `total > 0`, the brand's window-material total switches from the
    # per-opening bucket sum to this single package number. Contractor
    # use case: rep / inside-sales hand-quotes the whole window package
    # (oversize, special shapes, frozen products). Labor + accessories
    # + sales tax + profit all calc normally on top. Per-brand: Vero
    # quote is independent from the Mezzo quote.
    vero_package_quote: Optional["WindowPackageQuote"] = None
    mezzo_package_quote: Optional["WindowPackageQuote"] = None
    photos: List[str] = []
    status_label: str = "draft"
    # Soffit eave overhang in inches (12" default). Drives the
    # `Pieces = (Overhang × Length) ÷ panel area` math on the Vinyl
    # Soffit line — contractor adjusts once per job in Job Info.
    overhang_in: float = 12.0
    # Iter 78aj — list of porch ceilings (length × width). Their total
    # sqft feeds the same soffit formula as eaves × overhang. Empty by
    # default; contractor adds porches manually in the Job Info panel
    # (or via the HOVER preview modal before applying).
    porch_ceilings: List[PorchCeiling] = []
    # Photo Measure: human-readable summary of masked-out "no-siding"
    # zones (e.g. "Brick: 220 ft²; Garage door: 168 ft²") so the
    # customer PDF / email can show what was excluded from the siding
    # qty. `photo_zones_deducted_sqft` is the rolled-up total. Both
    # default to empty/0 — only populated when the contractor uses the
    # Photo Measure "Mask zone" tool.
    photo_zones_summary: str = ""
    photo_zones_deducted_sqft: float = 0
    # Iter 71 (2026-06-22): persist HOVER-extracted measurements on the
    # estimate so the customer PDF / email can render a per-elevation
    # breakdown (and other future displays like drip-edge totals, story
    # premium banners, etc.) without re-running the LLM. Populated by the
    # HOVER apply flow with whatever the parser returned. Free-form dict
    # so adding new extracted fields (Iter 70 banked 6) doesn't require
    # a schema bump on each addition.
    hover_measurements: Optional[Dict[str, Any]] = None


class MezzoOpening(BaseModel):
    """One quoted Mezzo window opening. Width + height drive the
    United Inches (UI) which snaps to a bucket on Mezzo's per-size
    price matrix. Per-opening adders carry their own qty + computed
    cost at save time so material-list / PDF rendering stays cheap."""
    id: str  # UUID; frontend-generated so optimistic UI works
    product_type: str  # e.g. "Mezzo Double Hung"
    label: str = ""    # optional "Kitchen — west" annotation
    width: float = 0   # inches
    height: float = 0  # inches
    qty: float = 1
    # Snapshotted base price (per-window mat from the bucket lookup at
    # save time). Lets the backend compute totals without re-resolving
    # the catalog matrix.
    base_mat: float = 0
    # Resolved bucket label (e.g. "32-73 UI") snapshotted at save time
    # for material-list / PDF rendering.
    bucket_label: str = ""
    # Selected adders. We reuse EstimateLineAdder so calc_totals can
    # treat openings the same way it treats line.adders, but `mat`
    # here is the PER-OPENING cost (sqft adders are pre-computed by
    # frontend at toggle time; flat adders are looked up by bucket).
    adders: List[EstimateLineAdder] = []


class VeroOpening(BaseModel):
    """One quoted Vero window opening. UI-bucket products use width +
    height to derive United Inches → bucket → base price; the Patio Door
    uses a fixed `model` instead. Per Iter 44 Vero mirrors Mezzo's model:
    a single `adders[]` list replaces the legacy glass / tempered /
    premium fields (which remain on the schema for backward compat with
    estimates saved before the migration)."""
    id: str  # UUID; frontend-generated so optimistic UI works
    product_type: str
    sizing: str = "ui_bucket"
    label: str = ""
    width: float = 0
    height: float = 0
    model: str = ""
    qty: float = 1
    sister_color: str = ""
    # Iter 44: Mezzo-style per-opening adders.
    adders: List[EstimateLineAdder] = []
    # Snapshots (computed at save time so PDF / list rendering is cheap)
    bucket_label: str = ""
    base_mat: float = 0
    # ─── Deprecated since Iter 44; kept for historical estimates only ───
    glass_package: str = ""
    tempered_upcharge: str = ""
    premium_options: List[str] = []
    glass_mat: float = 0
    tempered_mat: float = 0
    premium_mat: float = 0


class WindowPackageQuote(BaseModel):
    """Iter 57v — Per-brand window-package override. When `enabled` and
    `total > 0`, the brand's window-material total switches from the
    per-opening bucket sum to `total`. `reference` is a contractor-
    facing memo (e.g. "Vero quote #VR-44892" or rep name); `notes` is
    optional free text for spec details (color / glass / lead time)."""
    enabled: bool = False
    total: float = 0
    reference: str = ""
    notes: str = ""


EstimateIn.model_rebuild()


class EmailQuoteIn(BaseModel):
    recipient_email: EmailStr
    subject: Optional[str] = None
    message: Optional[str] = None
    html_quote: str
    accept_token: Optional[str] = None  # client-generated UUID4 for the public accept link
    # ONE MONEY SURFACE (ruled 2026-07-23): the tab scope the quote was
    # composed from — the accept page derives its total from the SAME
    # scope, never an all-tab sum. None = all tabs (single-line estimates).
    quote_tab_scope: Optional[List[str]] = None


class CustomerAcceptIn(BaseModel):
    note: Optional[str] = None
