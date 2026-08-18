"""SEND-48 pins — ZONE BINDING (per-surface, authorized).

Rules pinned:
- Binding is per-surface: one face body ("front") or one gable
  ("gable:front"), never whole-house, when the surface snapshot exists.
- Law A: a zone REPLACES its surface's derived number; the previous
  system number stays visible (line superseded_qty + per-surface
  overlay_replaced_surfaces).
- A REFUSING face is fully bindable (snapshot 0.0 + the named refusal)
  — the primary purpose of the feature.
- Triangles and multi-part faces bind (≥3 vertices; multiple polygons
  per surface, the surface subtracted once).
- PROPOSED zones are provisional: they never feed a quantity; a human
  confirm/bump makes them HUMAN. Human zones live in their own
  collection and survive re-reads (unchanged from MUV).
- Pre-SEND-48 zones (no snapshot) keep the legacy whole-class
  replacement — both modes named on the line.
"""
import sys

sys.path.insert(0, "/app/backend")

from routes.pdf_overlay import (_face_ok, apply_overlay_to_takeoff,
                                surface_derived_snapshot)

SCALE = {"mode": "trace", "p1": [0.1, 0.1], "p2": [0.1, 0.6],
         "real_ft": 10.0}


def _lines():
    return [{"tab": "vinyl", "section": "Siding", "unit": "SQ",
             "qty": 44.0, "raw_qty": 44.0, "qty_src": "derived",
             "name": "D4 Clapboard"}]


def _zone(face_id, sqft, surface=None, refusal=None, provenance="human",
          verts=3):
    return {"id": f"z-{face_id}-{sqft}", "face_id": face_id,
            "material_class": "siding", "sqft": sqft,
            "vertices_pct": [[0.1, 0.1], [0.5, 0.1], [0.3, 0.6]][:verts],
            "derived_baseline_qty": 44.0,
            "surface_derived_sqft": surface,
            "surface_refusal": refusal,
            "provenance": provenance}


class TestFaceGrammar:
    def test_gable_faces_are_bindable_surfaces(self):
        assert _face_ok("gable:front") and _face_ok("gable:left")

    def test_bogus_gable_rejected(self):
        assert not _face_ok("gable:") and not _face_ok("gable:roof")


class TestPerSurfaceLawA:
    def test_zone_replaces_one_surface_not_the_house(self):
        # front body derived 500 ft²; human triangle of 300 ft² replaces
        # THAT surface only: 44 SQ − 5 + 3 = 42 SQ.
        out = apply_overlay_to_takeoff(
            _lines(), [_zone("front", 300.0, surface=500.0)])
        sid = out[0]
        assert sid["qty"] == 42.0
        assert sid["superseded_qty"] == 44.0          # previous number SHOWN
        assert sid["overlay_per_surface"] is True
        assert sid["overlay_replaced_surfaces"] == [
            {"face_id": "front", "superseded_sqft": 500.0, "refusal": None}]
        assert sid["qty_src"] == "human"

    def test_refusing_face_is_fully_bindable(self):
        # THE PRIMARY PURPOSE: the face refused (0.0 + named reason); the
        # zone supplies its area on top of the untouched rest-of-house.
        refusal = ("Two different wall heights found on this elevation "
                   "(9'-1\" and 9'-11\"). ...")
        out = apply_overlay_to_takeoff(
            _lines(), [_zone("front", 900.0, surface=0.0, refusal=refusal)])
        sid = out[0]
        assert sid["qty"] == 53.0                     # 44 + 9
        assert sid["overlay_replaced_surfaces"][0]["refusal"] == refusal

    def test_gable_surface_binds_independently_of_the_body(self):
        out = apply_overlay_to_takeoff(
            _lines(), [_zone("gable:left", 120.0, surface=80.0)])
        sid = out[0]
        assert sid["qty"] == round(44.0 + (120.0 - 80.0) / 100.0, 2)
        assert sid["overlay_replaced_surfaces"][0]["face_id"] == "gable:left"

    def test_multipart_face_sums_zones_but_subtracts_the_surface_once(self):
        z1 = _zone("front", 200.0, surface=500.0)
        z2 = dict(_zone("front", 250.0, surface=500.0), id="z2")
        out = apply_overlay_to_takeoff(_lines(), [z1, z2])
        sid = out[0]
        # 44 − 5 + 4.5 = 43.5 (surface subtracted ONCE)
        assert sid["qty"] == 43.5
        assert sid["overlay_merged"] is True

    def test_triangle_binds(self):
        out = apply_overlay_to_takeoff(
            _lines(), [_zone("front", 100.0, surface=0.0, verts=3)])
        assert out[0]["overlay_superseded"] is True

    def test_legacy_zone_without_snapshot_keeps_whole_class_replacement(self):
        out = apply_overlay_to_takeoff(
            _lines(), [_zone("front", 900.0, surface=None)])
        sid = out[0]
        assert sid["qty"] == 9.0                      # legacy MUV math
        assert "overlay_per_surface" not in sid


class TestProposedZonesAreProvisional:
    def test_proposed_zone_feeds_no_quantity(self):
        out = apply_overlay_to_takeoff(
            _lines(), [_zone("front", 900.0, surface=0.0,
                             provenance="proposed")])
        sid = out[0]
        assert sid["qty"] == 44.0
        assert "overlay_superseded" not in sid or not sid["overlay_superseded"]

    def test_only_human_zones_enter_alongside_proposed(self):
        out = apply_overlay_to_takeoff(
            _lines(), [_zone("front", 900.0, surface=0.0,
                             provenance="proposed"),
                       _zone("front", 300.0, surface=500.0)])
        assert out[0]["qty"] == 42.0


class TestSurfaceSnapshot:
    EST = {"hover_measurements": {"_wall_walk_detail": [
        {"label": "front", "body_sqft": 512.5, "body_refusal": None,
         "gable_sqft": 84.0, "gable_refusal": None},
        {"label": "left", "body_sqft": 0.0,
         "body_refusal": ("Two different wall heights found on this "
                          "elevation (6'-0\" and 9'-1\"). ..."),
         "gable_sqft": None,
         "gable_refusal": "wall width not read — gable area not derivable"},
        {"label": "back", "refused": True,
         "reason": "footprint closure refused"}]}}

    def test_derived_body_snapshot(self):
        assert surface_derived_snapshot(self.EST, "front") == (512.5, None)

    def test_refused_body_snapshot_carries_the_named_reason(self):
        sqft, ref = surface_derived_snapshot(self.EST, "left")
        assert sqft == 0.0 and "Two different wall heights" in ref

    def test_gable_snapshot(self):
        assert surface_derived_snapshot(self.EST, "gable:front") == (84.0, None)

    def test_refused_gable_snapshot(self):
        sqft, ref = surface_derived_snapshot(self.EST, "gable:left")
        assert sqft == 0.0 and "gable area not derivable" in ref

    def test_closure_refused_face_snapshot(self):
        sqft, ref = surface_derived_snapshot(self.EST, "back")
        assert sqft == 0.0 and "footprint closure refused" in ref

    def test_no_walk_detail_means_legacy(self):
        assert surface_derived_snapshot({}, "front") == (None, None)

    def test_dormer_stays_legacy(self):
        assert surface_derived_snapshot(self.EST, "dormer:left") == (None, None)
