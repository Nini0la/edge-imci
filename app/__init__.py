"""EdgeIMCI prototype application layer.

This package contains the application/service layer that sits between the
frontend UI and the deterministic clinical core. It is deliberately thin and
isolated from the clinical engine.

The key seam is the ``EncounterExtractor`` interface. The service can use either
the offline fixture extractor or the provisionally selected Qwen3-0.6B Modal
checkpoint without changing the UI or deterministic clinical core.
"""
