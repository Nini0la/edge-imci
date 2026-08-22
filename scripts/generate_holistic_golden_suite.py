#!/usr/bin/env python3
"""Regenerate the proposed product-level holistic golden semantic suite."""

from edge_imci.generation.holistic_golden import (
    DEFAULT_APPROVAL_YAML_PATH,
    DEFAULT_JSONL_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_REVIEW_PATH,
    DEFAULT_SCOPE_DISPOSITIONS_YAML_PATH,
    DEFAULT_YAML_PATH,
    write_holistic_golden_suite,
)


if __name__ == "__main__":
    records = write_holistic_golden_suite()
    print(f"wrote {len(records)} holistic semantic cases to {DEFAULT_JSONL_PATH}")
    print(f"wrote YAML mirror to {DEFAULT_YAML_PATH}")
    print(f"wrote suite manifest to {DEFAULT_MANIFEST_PATH}")
    print(f"wrote scope-disposition YAML mirror to {DEFAULT_SCOPE_DISPOSITIONS_YAML_PATH}")
    print(f"wrote approval YAML mirror to {DEFAULT_APPROVAL_YAML_PATH}")
    print(f"wrote review package to {DEFAULT_REVIEW_PATH}")
