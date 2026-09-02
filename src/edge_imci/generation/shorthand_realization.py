"""Deterministic realization checks for subjectless, unpunctuated PHC shorthand."""

from __future__ import annotations

import re
from typing import Any


_EXPLICIT_SUBJECT = re.compile(
    r"\b(?:the\s+)?(?:child|patient|baby|infant|boy|girl|he|she|they|it)\b",
    re.IGNORECASE,
)
_HEADING = re.compile(r"(?im)^\s*(?:history|assessment|examination|exam|plan|findings)\s*:")
_BULLET = re.compile(r"(?m)^\s*(?:[-*+]\s+|\d+[.)]\s+)")
_ORDINARY_PROSE = re.compile(
    r"\b(?:the child|the patient|the baby|he is|she is|they are|it is|"
    r"was brought|was seen|presents? with|reports? that|caregiver says)\b",
    re.IGNORECASE,
)
_CLINICAL_FRAGMENT = re.compile(
    r"\b(?:no|yes|temp|temperature|rr|respiratory rate|pulse|spo2|"
    r"cough|diarrh(?:oe|e)a|fever|vomit|stridor|indrawing|convuls|"
    r"drink|breastfeed|pain|discharge|stiff neck|letharg|unconscious)\b",
    re.IGNORECASE,
)


def assess_shorthand_realization(text: str) -> dict[str, Any]:
    """Assess style only; semantic correctness remains a separate gate."""

    normalized = " ".join(text.split())
    without_decimals = re.sub(r"(?<=\d)\.(?=\d)", "", normalized)
    subject_omission = _EXPLICIT_SUBJECT.search(normalized) is None
    punctuation_loss = re.search(r"[.!?;]", without_decimals) is None
    prohibited_headings_or_bullets = bool(
        _HEADING.search(text) or _BULLET.search(text)
    )
    accidental_ordinary_prose = bool(_ORDINARY_PROSE.search(normalized))
    fragment_telegraphic = bool(
        normalized
        and _CLINICAL_FRAGMENT.search(normalized)
        and subject_omission
        and not accidental_ordinary_prose
    )
    joint = subject_omission and punctuation_loss
    errors: list[str] = []
    if not subject_omission:
        errors.append("SUBJECT_PRESENT")
    if not punctuation_loss:
        errors.append("SENTENCE_PUNCTUATION_PRESENT")
    if not fragment_telegraphic:
        errors.append("NOT_TELEGRAPHIC_FRAGMENT")
    if prohibited_headings_or_bullets:
        errors.append("PROHIBITED_HEADING_OR_BULLET")
    if accidental_ordinary_prose:
        errors.append("ORDINARY_PROSE_REALIZATION")
    return {
        "profile": "SUBJECTLESS_UNPUNCTUATED_SHORTHAND",
        "subject_omission": subject_omission,
        "punctuation_loss": punctuation_loss,
        "fragment_telegraphic": fragment_telegraphic,
        "prohibited_headings_or_bullets": prohibited_headings_or_bullets,
        "accidental_ordinary_prose": accidental_ordinary_prose,
        "joint_subject_omission_and_punctuation_loss": joint,
        "style_pass": joint
        and fragment_telegraphic
        and not prohibited_headings_or_bullets
        and not accidental_ordinary_prose,
        "error_codes": errors,
    }
