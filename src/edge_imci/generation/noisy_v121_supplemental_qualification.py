"""Run the remaining 19 parents for noisy English v1.2.1 qualification."""

import json

from edge_imci.generation import input_style_pathway_qualification as base
from edge_imci.generation.holistic_variants import ROOT


RUN_ID = "holistic-noisy-v1-2-1-supplemental-qualification-gpt41-20250414-v1"
EXCLUDED = {
    "hpg-008-resp-age-2-rate-50",
    "hpg-014-resp-chest-hiv-positive",
    "hpg-052-fever-identified-bacterial-cause",
    "hpg-027-diarrhoea-no-dehydration",
    "hpg-068-cross-four-pathways",
}


def _remaining_cases() -> tuple[str, ...]:
    selection_path = (
        ROOT / "configs" / "generation" / "nigerian_english_v1_2_pathway_pilot_selection.json"
    )
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    result = tuple(
        item["semantic_case_id"]
        for item in selection["cases"]
        if item["semantic_case_id"] not in EXCLUDED
    )
    if len(result) != 19:
        raise ValueError("noisy v1.2.1 supplemental selection must contain 19 parents")
    return result


def _configure() -> None:
    base.RUN_ID = RUN_ID
    base.RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
    base.AUTHORIZATION_PATH = (
        ROOT
        / "configs"
        / "generation"
        / "noisy_v1_2_1_supplemental_qualification_authorization.json"
    )
    base.AUTHORIZATION_ID = (
        "edge-imci-noisy-v1-2-1-supplemental-qualification-authorization-v1"
    )
    base.EXPECTED_ATTEMPTS = 19
    base.EXPECTED_STYLES = 1
    base.EXPECTED_PARENT_CASES_PER_STYLE = 19
    base.MAXIMUM_BUDGET_USD = 0.8
    base.FIRST_GATE_ATTEMPTS = 0
    base.SELECTED_CASE_IDS = _remaining_cases()
    base.STYLE_CONFIGURATIONS = (
        {
            "variant_style": "NOISY_TYPED_ENGLISH",
            "strategy_id": "phc-noisy-typed-english-v1",
            "prompt_path": "prompts/holistic_language_variants/phc_noisy_typed_english_v1_2_1.txt",
            "prompt_id": "edge-imci-phc-noisy-typed-english",
            "prompt_version": "1.2.1",
            "noise_profile": [
                "ARTICLE_OMISSION",
                "PUNCTUATION_LOSS",
                "CASING_VARIATION",
                "SENTENCE_FRAGMENTS",
                "SPELLING_NOISE",
            ],
        },
    )


def main() -> int:
    _configure()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
