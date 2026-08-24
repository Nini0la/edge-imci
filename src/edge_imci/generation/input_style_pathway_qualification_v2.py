"""Run staged pathway qualification with Nigerian English prompt v1.3.1."""

from __future__ import annotations

from edge_imci.generation import input_style_pathway_qualification as base


RUN_ID = "holistic-input-style-pathway-qualification-gpt41-20250414-v2"


def configure() -> None:
    base.RUN_ID = RUN_ID
    base.RUN_DIR = base.ROOT / "experiments" / "generation" / RUN_ID
    base.AUTHORIZATION_PATH = (
        base.ROOT
        / "configs"
        / "generation"
        / "input_style_pathway_qualification_authorization_v2.json"
    )
    base.AUTHORIZATION_ID = (
        "edge-imci-input-style-pathway-qualification-authorization-v2"
    )
    styles = [dict(item) for item in base.STYLE_CONFIGURATIONS]
    styles[0]["prompt_path"] = (
        "prompts/holistic_language_variants/phc_nigerian_english_v1_3_1.txt"
    )
    styles[0]["prompt_version"] = "1.3.1"
    base.STYLE_CONFIGURATIONS = tuple(styles)


def main() -> int:
    configure()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
