"""Run the exact-slot 1,892-attempt continuation after T1 remediation."""

from edge_imci.generation import structured_extraction_bulk_wave as base
from edge_imci.generation.holistic_variants import ROOT


RUN_ID = "structured-extraction-language-bulk-gpt41-20250414-v4"


def _configure() -> None:
    base.CONTRACT_PATH = ROOT / "configs/generation/structured_extraction_bulk_wave_v4.json"
    base.CONTRACT_ID = "edge-imci-structured-extraction-bulk-wave-v4"
    base.RUN_ID = RUN_ID
    base.RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
    base.STYLE_RELEASE_PATH = ROOT / "configs/generation/input_style_qualification_release_v2.json"
    base.SKIP_PREFIX_ATTEMPTS = 0
    base.SKIP_COMPLETED_RUN_ID = None
    base.SKIP_COMPLETED_RUN_IDS = (
        "structured-extraction-language-bulk-gpt41-20250414-v1",
        "structured-extraction-language-bulk-gpt41-20250414-v3",
    )
    base.STYLE_CONFIGURATIONS = (
        {
            "variant_style": "NIGERIAN_ENGLISH",
            "strategy_id": "phc-nigerian-english-v1",
            "prompt_path": "prompts/holistic_language_variants/phc_nigerian_english_v1_3_4.txt",
            "prompt_id": "edge-imci-phc-nigerian-english",
            "prompt_version": "1.3.4",
            "noise_profile": [],
        },
        {
            "variant_style": "NIGERIAN_PIDGIN",
            "strategy_id": "phc-nigerian-pidgin-v1",
            "prompt_path": "prompts/holistic_language_variants/phc_nigerian_pidgin_v1_2_3.txt",
            "prompt_id": "edge-imci-phc-nigerian-pidgin",
            "prompt_version": "1.2.3",
            "noise_profile": [],
        },
        {
            "variant_style": "NOISY_TYPED_ENGLISH",
            "strategy_id": "phc-noisy-typed-english-v1",
            "prompt_path": "prompts/holistic_language_variants/phc_noisy_typed_english_v1_2_4.txt",
            "prompt_id": "edge-imci-phc-noisy-typed-english",
            "prompt_version": "1.2.4",
            "noise_profile": [
                "ARTICLE_OMISSION", "PUNCTUATION_LOSS", "CASING_VARIATION",
                "SENTENCE_FRAGMENTS", "SPELLING_NOISE"
            ],
        },
        {
            "variant_style": "TELEGRAPHIC_PHC_NOTE",
            "strategy_id": "phc-telegraphic-note-v1",
            "prompt_path": "prompts/holistic_language_variants/phc_telegraphic_note_v1_1_2.txt",
            "prompt_id": "edge-imci-phc-telegraphic-note",
            "prompt_version": "1.1.2",
            "noise_profile": [
                "ABBREVIATION_DENSITY_MEDIUM", "SENTENCE_FRAGMENTS",
                "TELEGRAPHIC_COMPRESSION"
            ],
        },
    )


def main() -> int:
    _configure()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
