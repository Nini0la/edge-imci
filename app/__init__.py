"""EdgeIMCI prototype application layer.

This package contains the application/service layer that sits between the
frontend UI and the deterministic clinical core. It is deliberately thin and
isolated from the clinical engine.

The key seam is the ``EncounterExtractor`` interface. The current implementation
is a stub that maps known fixture texts to frozen encounter structures. When the
fine-tuned extraction model is ready, it will be swapped in at this boundary
without requiring UI or downstream changes.
"""
