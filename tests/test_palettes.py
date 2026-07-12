"""Every themed palette must pass the accessibility checks — by computation,
not by eye. ``classic`` is exempt (documented as the unvalidated legacy style).
"""
import pytest

from data_analysis import theming
from data_analysis.palette_check import (
    CVD_TARGET,
    delta_e_cvd,
    validate_palette,
)

VALIDATED = [name for name in theming.THEMES if name != "classic"]


def _surface(name: str) -> tuple[str, str]:
    rc = theming.THEMES[name]["rc"]
    surface = rc.get("figure.facecolor", "#ffffff")
    mode = "dark" if name == "dark" else "light"
    return mode, surface


@pytest.mark.parametrize("name", VALIDATED)
def test_theme_palette_passes_accessibility_checks(name):
    mode, surface = _surface(name)
    result = validate_palette(theming.THEMES[name]["palette"], mode, surface)
    assert result["lightness_ok"], f"{name}: {result['lightness_violations']}"
    assert result["chroma_ok"], f"{name}: {result['chroma_violations']}"
    assert result["cvd_ok"], f"{name}: worst adjacent pair {result['cvd_worst']}"
    # Contrast is a hard requirement here (static PNGs have no hover relief).
    assert result["contrast_ok"], f"{name}: {result['contrast_warnings']}"


@pytest.mark.parametrize("name", VALIDATED)
def test_theme_has_ramp_definitions(name):
    spec = theming.THEMES[name]
    assert spec["sequential_cmap"]
    assert spec["diverging_cmap"]


def test_validator_catches_known_bad_palette():
    """The pre-refactor 'vibrant' yellow/lime pair was indistinguishable under
    protanopia (ΔE 5.5) — the validator must keep failing it."""
    assert delta_e_cvd("#ffca3a", "#8ac926", "protan") < CVD_TARGET
    old_vibrant = ["#ff595e", "#1982c4", "#8ac926", "#ffca3a", "#6a4c93",
                   "#36bfb1", "#ff7bac", "#4267ac"]
    assert not validate_palette(old_vibrant, "light", "#ffffff")["passed"]


def test_validator_agrees_with_reference_measurements():
    """Calibration pins against the reference JS validator so the Python port
    can't silently drift: chroma of two known slots, one contrast ratio, and
    one CVD distance, all measured independently."""
    from data_analysis.palette_check import contrast_ratio, oklch

    assert round(oklch("#3fa9bc")[1], 3) == 0.099
    assert round(oklch("#77808c")[1], 3) == 0.021
    assert round(contrast_ratio("#e8853d", "#fcfcfb"), 2) == 2.6
    assert round(delta_e_cvd("#d95b5b", "#43a57c", "protan"), 1) == 15.3
