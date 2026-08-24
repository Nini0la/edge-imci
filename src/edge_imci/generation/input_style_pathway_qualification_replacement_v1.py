"""Run the traceable replacement for the v3 Pidgin transport failure."""

from edge_imci.generation import input_style_pathway_qualification as base
from edge_imci.generation.holistic_variants import ROOT


RUN_ID = "holistic-input-style-pathway-qualification-replacement-gpt41-20250414-v1"


def _configure() -> None:
    base.RUN_ID = RUN_ID
    base.RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
    base.AUTHORIZATION_PATH = (
        ROOT
        / "configs"
        / "generation"
        / "input_style_pathway_qualification_replacement_authorization_v1.json"
    )
    base.AUTHORIZATION_ID = (
        "edge-imci-input-style-pathway-qualification-replacement-authorization-v1"
    )
    base.EXPECTED_ATTEMPTS = 1
    base.EXPECTED_STYLES = 1
    base.EXPECTED_PARENT_CASES_PER_STYLE = 1
    base.MAXIMUM_BUDGET_USD = 0.1
    base.FIRST_GATE_ATTEMPTS = 0
    base.SELECTED_CASE_IDS = ("hpg-028-diarrhoea-some-dehydration",)
    base.STYLE_CONFIGURATIONS = (
        {
            "variant_style": "NIGERIAN_PIDGIN",
            "strategy_id": "phc-nigerian-pidgin-v1",
            "prompt_path": "prompts/holistic_language_variants/phc_nigerian_pidgin_v1_1.txt",
            "prompt_id": "edge-imci-phc-nigerian-pidgin",
            "prompt_version": "1.1.0",
            "noise_profile": [],
        },
    )


def main() -> int:
    _configure()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
