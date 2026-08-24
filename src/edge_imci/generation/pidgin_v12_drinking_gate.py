"""Run the three-parent Nigerian Pidgin v1.2 drinking-boundary gate."""

from edge_imci.generation import input_style_pathway_qualification as base
from edge_imci.generation.holistic_variants import ROOT


RUN_ID = "holistic-pidgin-v1-2-drinking-gate-gpt41-20250414-v1"


def _configure() -> None:
    base.RUN_ID = RUN_ID
    base.RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
    base.AUTHORIZATION_PATH = (
        ROOT / "configs" / "generation" / "pidgin_v1_2_drinking_gate_authorization.json"
    )
    base.AUTHORIZATION_ID = "edge-imci-pidgin-v1-2-drinking-gate-authorization-v1"
    base.EXPECTED_ATTEMPTS = 3
    base.EXPECTED_STYLES = 1
    base.EXPECTED_PARENT_CASES_PER_STYLE = 3
    base.MAXIMUM_BUDGET_USD = 0.15
    base.FIRST_GATE_ATTEMPTS = 0
    base.SELECTED_CASE_IDS = (
        "hpg-027-diarrhoea-no-dehydration",
        "hpg-028-diarrhoea-some-dehydration",
        "hpg-075-contradiction-drinking",
    )
    base.STYLE_CONFIGURATIONS = (
        {
            "variant_style": "NIGERIAN_PIDGIN",
            "strategy_id": "phc-nigerian-pidgin-v1",
            "prompt_path": "prompts/holistic_language_variants/phc_nigerian_pidgin_v1_2.txt",
            "prompt_id": "edge-imci-phc-nigerian-pidgin",
            "prompt_version": "1.2.0",
            "noise_profile": [],
        },
    )


def main() -> int:
    _configure()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
