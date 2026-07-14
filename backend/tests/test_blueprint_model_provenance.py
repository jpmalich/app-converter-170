"""Blueprint model-pin provenance (Iter 112, Howard's audit follow-up).

Finding: the blueprint pipeline's Opus 4.5 pin was INHERITED from
AI-measure's then-default at feature birth (2026-06-18) — never
consciously chosen, never validated. These pins keep the flag honest
until a validated-model decision lands, and guarantee blueprint runs
stamp model_config + prompt hash so that decision has provenance."""
import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv(Path("/app/backend/.env"))

import routes.ai_blueprint as bp  # noqa: E402

SRC = Path("/app/backend/routes/ai_blueprint.py").read_text()


def test_pin_flagged_as_unvalidated_inherited():
    assert bp.MODEL_VALIDATION_STATUS == (
        "inherited-default — validated-model decision pending")
    assert "PROVENANCE FLAG" in SRC


def test_runs_stamp_model_config_with_prompt_hash():
    h = bp._blueprint_prompt_hash()
    assert isinstance(h, str) and len(h) == 16
    # the done-result writes model_config with validation status + hash
    assert '"model_config": {' in SRC
    assert "MODEL_VALIDATION_STATUS" in SRC
    assert "_blueprint_prompt_hash()" in SRC
