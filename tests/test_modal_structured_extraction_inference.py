from __future__ import annotations

import json

from edge_imci.inference.modal_structured_extraction import (
    DEFAULT_DEMO_TEXT,
    MODEL_WEIGHTS_SHA256,
    TRAINING_RUN_ID,
    inference_messages,
)
from edge_imci.training.structured_extraction import (
    STRUCTURED_EXTRACTION_SYSTEM_INSTRUCTION,
)


def test_demo_uses_the_completed_training_run_and_exact_system_instruction() -> None:
    messages = inference_messages(DEFAULT_DEMO_TEXT)
    assert TRAINING_RUN_ID == "251039a3-4adc-4e74-8c30-069eb8aca6de"
    assert MODEL_WEIGHTS_SHA256 == (
        "86bb2507e5e7d04ad35c6c933923b902d21652bd04c401055a97a0d4485fd76a"
    )
    assert "able to drink or breastfeed" in DEFAULT_DEMO_TEXT
    assert "not lethargic or unconscious" in DEFAULT_DEMO_TEXT
    assert messages == [
        {"role": "system", "content": STRUCTURED_EXTRACTION_SYSTEM_INSTRUCTION},
        {"role": "user", "content": DEFAULT_DEMO_TEXT},
    ]


def test_novel_demo_is_not_an_exact_campaign_submission() -> None:
    campaign = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "data/training_sources/structured_extraction_campaign_v1/chat_messages.jsonl"
    )
    submissions = {
        json.loads(line)["messages"][1]["content"]
        for line in campaign.read_text(encoding="utf-8").splitlines()
    }
    assert DEFAULT_DEMO_TEXT not in submissions
