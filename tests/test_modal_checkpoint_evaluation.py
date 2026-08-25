from __future__ import annotations

import pytest

from edge_imci.evaluation.modal_checkpoint import _safe_identifier


def test_remote_evaluation_identifiers_are_restricted() -> None:
    assert _safe_identifier("cell-001", "cell") == "cell-001"
    with pytest.raises(ValueError, match="invalid cell"):
        _safe_identifier("../cell", "cell")
