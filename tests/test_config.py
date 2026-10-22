"""Tests for environment configuration parsing.

Security-relevant booleans must fail loudly on a value they do not
understand: treating ``VEILRENDER_EGRESS_PROXY=enable`` as false would start
the service with enforcement silently disabled.
"""

from __future__ import annotations

import pytest

from veilrender.config import _env_bool

_VAR = "VEILRENDER_TEST_BOOL"


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_truthy_values(monkeypatch, value: str) -> None:
    monkeypatch.setenv(_VAR, value)
    assert _env_bool(_VAR, False) is True


@pytest.mark.parametrize("value", ["0", "false", "FALSE", "no", "off"])
def test_falsy_values(monkeypatch, value: str) -> None:
    monkeypatch.setenv(_VAR, value)
    assert _env_bool(_VAR, True) is False


def test_default_when_unset(monkeypatch) -> None:
    monkeypatch.delenv(_VAR, raising=False)
    assert _env_bool(_VAR, True) is True
    assert _env_bool(_VAR, False) is False


def test_empty_means_unset(monkeypatch) -> None:
    # `VAR=` is the usual way to leave an optional variable unset.
    monkeypatch.setenv(_VAR, "")
    assert _env_bool(_VAR, True) is True
    assert _env_bool(_VAR, False) is False


@pytest.mark.parametrize("value", ["enable", "disable", "2", "truthy"])
def test_invalid_value_raises(monkeypatch, value: str) -> None:
    monkeypatch.setenv(_VAR, value)
    with pytest.raises(ValueError, match=_VAR):
        _env_bool(_VAR, False)
