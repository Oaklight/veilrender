"""Tests for font resolution logic."""

from veilrender.fonts import FONT_ALIASES, FONT_REGISTRY, _resolve_entries


def test_preset_name():
    entries = _resolve_entries(["noto-sans-sc"])
    assert len(entries) == 1
    assert entries[0][0] == "noto-sans-sc.ttf"
    assert entries[0][1] == FONT_REGISTRY["noto-sans-sc"]


def test_alias_expansion():
    entries = _resolve_entries(["cjk"])
    assert len(entries) == len(FONT_ALIASES["cjk"])
    names = [e[0] for e in entries]
    for font in FONT_ALIASES["cjk"]:
        assert f"{font}.ttf" in names


def test_i18n_alias():
    entries = _resolve_entries(["i18n"])
    assert len(entries) == len(FONT_ALIASES["i18n"])


def test_custom_url():
    url = "https://example.com/path/MyFont.ttf"
    entries = _resolve_entries([url])
    assert len(entries) == 1
    assert entries[0] == ("MyFont.ttf", url)


def test_custom_url_no_filename():
    entries = _resolve_entries(["https://example.com/"])
    assert len(entries) == 1
    assert entries[0][0] == "custom-font.ttf"


def test_dedup():
    entries = _resolve_entries(["noto-sans-sc", "cjk"])
    names = [e[0] for e in entries]
    assert names.count("noto-sans-sc.ttf") == 1


def test_mixed():
    entries = _resolve_entries([
        "noto-color-emoji",
        "cjk",
        "https://example.com/Custom.woff2",
    ])
    names = [e[0] for e in entries]
    assert "noto-color-emoji.ttf" in names
    assert "noto-sans-sc.ttf" in names
    assert "Custom.woff2" in names


def test_unknown_spec():
    entries = _resolve_entries(["nonexistent-font"])
    assert len(entries) == 0


def test_empty():
    entries = _resolve_entries([])
    assert entries == []
