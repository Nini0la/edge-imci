#!/usr/bin/env python3
"""Regenerate the bounded 16-case holistic golden-language calibration draft."""

from edge_imci.generation.holistic_language import (
    DEFAULT_CALIBRATION_PATH,
    DEFAULT_CALIBRATION_YAML_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_REVIEW_PATH,
    write_language_calibration,
)


if __name__ == "__main__":
    records = write_language_calibration()
    print(f"wrote {len(records)} language calibration records to {DEFAULT_CALIBRATION_PATH}")
    print(f"wrote YAML mirror to {DEFAULT_CALIBRATION_YAML_PATH}")
    print(f"wrote manifest to {DEFAULT_MANIFEST_PATH}")
    print(f"wrote review package to {DEFAULT_REVIEW_PATH}")
