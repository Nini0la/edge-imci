#!/usr/bin/env python3
"""Regenerate the complete 78-case holistic golden-language review draft."""

from edge_imci.generation.holistic_language_full import (
    DEFAULT_LANGUAGE_PATH,
    DEFAULT_LANGUAGE_YAML_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_REVIEW_PATH,
    write_full_language_suite,
)


if __name__ == "__main__":
    records = write_full_language_suite()
    print(f"wrote {len(records)} language records to {DEFAULT_LANGUAGE_PATH}")
    print(f"wrote YAML mirror to {DEFAULT_LANGUAGE_YAML_PATH}")
    print(f"wrote manifest to {DEFAULT_MANIFEST_PATH}")
    print(f"wrote review package to {DEFAULT_REVIEW_PATH}")
