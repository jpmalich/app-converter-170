"""THE PHOTO TAKEOFF SURFACE IS FOUR FILES NOW, NOT ONE (SEND-142 item 2).

NAMED PIN UPDATE, never a silent flip: the editor's right rail was split
into ScalePanel / QuantitiesPanel / MarksPanel with the shared mark
vocabulary in marks.js. Every pin that read the editor's source text asks
exactly the SAME question as before — it just has to read the whole
surface instead of one file. No pin's intent changed, no assertion was
relaxed, and `editor_surface()` FAILS LOUD if a panel file is missing, so
the surface cannot shrink silently and a pin cannot pass over a file that
quietly disappeared.
"""
import pathlib

EST = pathlib.Path("/app/frontend/src/components/estimate")
EDITOR_FILE = EST / "PhotoTakeoffEditor.jsx"
PANEL_FILES = [EST / "phototakeoff" / n for n in
               ("ScalePanel.jsx", "QuantitiesPanel.jsx", "MarksPanel.jsx",
                "marks.js")]
SURFACE_FILES = [EDITOR_FILE, *PANEL_FILES]


def editor_surface() -> str:
    for p in SURFACE_FILES:
        assert p.exists(), f"photo takeoff surface file missing: {p}"
    return "\n".join(p.read_text() for p in SURFACE_FILES)
