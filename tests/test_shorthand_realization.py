from edge_imci.generation.shorthand_realization import assess_shorthand_realization


def test_subjectless_unpunctuated_shorthand_passes() -> None:
    result = assess_shorthand_realization(
        "no cough no diarrhoea temp 38 rr 42 chest indrawing no stridor"
    )
    assert result["style_pass"] is True
    assert result["joint_subject_omission_and_punctuation_loss"] is True


def test_decimal_point_is_not_sentence_punctuation() -> None:
    result = assess_shorthand_realization("fever temp 38.5 no cough")
    assert result["punctuation_loss"] is True


def test_subject_and_sentence_punctuation_are_reported_independently() -> None:
    result = assess_shorthand_realization("The child has fever.")
    assert result["subject_omission"] is False
    assert result["punctuation_loss"] is False
    assert result["joint_subject_omission_and_punctuation_loss"] is False
    assert result["accidental_ordinary_prose"] is True


def test_heading_and_bullet_are_prohibited() -> None:
    result = assess_shorthand_realization("Assessment:\n- fever no cough")
    assert result["prohibited_headings_or_bullets"] is True
    assert result["style_pass"] is False
