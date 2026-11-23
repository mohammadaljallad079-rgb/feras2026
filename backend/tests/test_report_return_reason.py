"""A returned report must carry a reason a human can read (§11)."""

from __future__ import annotations

import pytest

from app.schemas import ReportReturn


def test_a_blank_reason_is_refused() -> None:
    with pytest.raises(ValueError):
        ReportReturn(reason="   ")


def test_a_two_character_reason_is_refused() -> None:
    with pytest.raises(ValueError):
        ReportReturn(reason=" ab ")


def test_a_real_reason_is_kept_without_padding() -> None:
    assert ReportReturn(reason="  رقم الإيراد غير مطابق للكشف  ").reason == (
        "رقم الإيراد غير مطابق للكشف"
    )
