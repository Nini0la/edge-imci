"""Run the 2,111-attempt continuation of the combined 2,142-attempt bulk wave."""

from edge_imci.generation import structured_extraction_bulk_wave as base
from edge_imci.generation.holistic_variants import ROOT


RUN_ID = "structured-extraction-language-bulk-gpt41-20250414-v2"


def _configure() -> None:
    base.CONTRACT_PATH = (
        ROOT / "configs" / "generation" / "structured_extraction_bulk_wave_v2.json"
    )
    base.CONTRACT_ID = "edge-imci-structured-extraction-bulk-wave-v2"
    base.RUN_ID = RUN_ID
    base.RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
    base.SKIP_PREFIX_ATTEMPTS = 31


def main() -> int:
    _configure()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
