"""Requalify the three remediated EdgeIMCI input-language prompts."""

from edge_imci.generation import input_style_pathway_qualification as base
from edge_imci.generation.holistic_variants import ROOT


RUN_ID = "holistic-input-style-pathway-qualification-gpt41-20250414-v3"


def _configure() -> None:
    base.RUN_ID = RUN_ID
    base.RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
    base.AUTHORIZATION_PATH = (
        ROOT
        / "configs"
        / "generation"
        / "input_style_pathway_qualification_authorization_v3.json"
    )
    base.AUTHORIZATION_ID = (
        "edge-imci-input-style-pathway-qualification-authorization-v3"
    )
    base.EXPECTED_ATTEMPTS = 72
    base.EXPECTED_STYLES = 3
    base.MAXIMUM_BUDGET_USD = 3.0
    base.FIRST_GATE_ATTEMPTS = 0
    base.STYLE_CONFIGURATIONS = (
        {
            "variant_style": "NIGERIAN_PIDGIN",
            "strategy_id": "phc-nigerian-pidgin-v1",
            "prompt_path": "prompts/holistic_language_variants/phc_nigerian_pidgin_v1_1.txt",
            "prompt_id": "edge-imci-phc-nigerian-pidgin",
            "prompt_version": "1.1.0",
            "noise_profile": [],
        },
        {
            "variant_style": "NOISY_TYPED_ENGLISH",
            "strategy_id": "phc-noisy-typed-english-v1",
            "prompt_path": "prompts/holistic_language_variants/phc_noisy_typed_english_v1_2.txt",
            "prompt_id": "edge-imci-phc-noisy-typed-english",
            "prompt_version": "1.2.0",
            "noise_profile": [
                "ARTICLE_OMISSION",
                "PUNCTUATION_LOSS",
                "CASING_VARIATION",
                "SENTENCE_FRAGMENTS",
                "SPELLING_NOISE",
            ],
        },
        {
            "variant_style": "TELEGRAPHIC_PHC_NOTE",
            "strategy_id": "phc-telegraphic-note-v1",
            "prompt_path": "prompts/holistic_language_variants/phc_telegraphic_note_v1_1.txt",
            "prompt_id": "edge-imci-phc-telegraphic-note",
            "prompt_version": "1.1.0",
            "noise_profile": [
                "ABBREVIATION_DENSITY_MEDIUM",
                "SENTENCE_FRAGMENTS",
                "TELEGRAPHIC_COMPRESSION",
            ],
        },
    )


def main() -> int:
    _configure()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
