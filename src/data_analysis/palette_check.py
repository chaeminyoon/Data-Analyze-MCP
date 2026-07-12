"""Palette accessibility validator — the color part of chart design is computable.

Implements the four categorical-palette checks used by the theme system:

1. **Lightness band** (OKLCH L): every slot must sit in a band that keeps marks
   visible but not glaring on the target surface.
2. **Chroma floor** (OKLCH C >= 0.1): a categorical slot below the floor reads
   as gray and stops carrying identity.
3. **CVD separation**: adjacent slots are simulated under protanopia /
   deuteranopia / tritanopia (Machado et al. 2009, severity 1.0) and must stay
   apart by at least ``CVD_TARGET`` CIE76 ΔE — palettes are read in slot order,
   so adjacency is what matters.
4. **Contrast vs surface** (WCAG relative luminance >= 3:1): a mark below 3:1
   needs relief (direct labels or a table view); we treat it as a warning.

All conversions are implemented from the published formulas (sRGB, OKLab by
Björn Ottosson, CIELAB D65, Machado 2009 matrices) — no extra dependencies.
"""
from __future__ import annotations

# Machado et al. (2009), severity 1.0, applied in linearized sRGB.
_CVD_MATRICES = {
    "protan": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deutan": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritan": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}

LIGHT_L_BAND = (0.43, 0.77)   # OKLCH lightness band on a light surface
DARK_L_BAND = (0.45, 0.70)    # steps for a dark surface sit lower
CHROMA_FLOOR = 0.10
CVD_TARGET = 12.0             # CIE76 ΔE; 8–12 is a floor band needing relief
CVD_FLOOR = 8.0
CONTRAST_MIN = 3.0

LIGHT_SURFACE = "#ffffff"
DARK_SURFACE = "#161a20"


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _linearize(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _delinearize(c: float) -> float:
    c = min(1.0, max(0.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _linear_rgb(hex_color: str) -> tuple[float, float, float]:
    return tuple(_linearize(c) for c in _hex_to_rgb(hex_color))


def relative_luminance(hex_color: str) -> float:
    r, g, b = _linear_rgb(hex_color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = sorted((relative_luminance(fg), relative_luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def oklch(hex_color: str) -> tuple[float, float]:
    """Return (L, C) in OKLCH (hue is irrelevant to the checks)."""
    r, g, b = _linear_rgb(hex_color)
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = l_ ** (1 / 3), m_ ** (1 / 3), s_ ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b2 = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, (a * a + b2 * b2) ** 0.5


def _lab(rgb_linear: tuple[float, float, float]) -> tuple[float, float, float]:
    """Linear sRGB -> CIELAB (D65)."""
    r, g, b = rgb_linear
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _simulate_cvd(hex_color: str, kind: str) -> tuple[float, float, float]:
    m = _CVD_MATRICES[kind]
    r, g, b = _linear_rgb(hex_color)
    return tuple(
        min(1.0, max(0.0, row[0] * r + row[1] * g + row[2] * b)) for row in m
    )


def delta_e_cvd(hex_a: str, hex_b: str, kind: str) -> float:
    """CIE76 ΔE between two colors as seen under a CVD simulation."""
    la = _lab(_simulate_cvd(hex_a, kind))
    lb = _lab(_simulate_cvd(hex_b, kind))
    return sum((x - y) ** 2 for x, y in zip(la, lb)) ** 0.5


def validate_palette(colors: list[str], mode: str = "light",
                     surface: str | None = None) -> dict:
    """Run the four checks. Returns a dict with pass/fail per check + details."""
    surface = surface or (LIGHT_SURFACE if mode == "light" else DARK_SURFACE)
    band = LIGHT_L_BAND if mode == "light" else DARK_L_BAND

    lightness_out, chroma_out, contrast_low = [], [], []
    for c in colors:
        L, chroma = oklch(c)
        if not band[0] <= L <= band[1]:
            lightness_out.append((c, round(L, 3)))
        if chroma < CHROMA_FLOOR:
            chroma_out.append((c, round(chroma, 3)))
        ratio = contrast_ratio(c, surface)
        if ratio < CONTRAST_MIN:
            contrast_low.append((c, round(ratio, 2)))

    worst = None
    for a, b in zip(colors, colors[1:]):
        for kind in _CVD_MATRICES:
            de = delta_e_cvd(a, b, kind)
            if worst is None or de < worst[3]:
                worst = (a, b, kind, de)

    return {
        "mode": mode,
        "surface": surface,
        "lightness_ok": not lightness_out,
        "lightness_violations": lightness_out,
        "chroma_ok": not chroma_out,
        "chroma_violations": chroma_out,
        "cvd_worst": {
            "pair": (worst[0], worst[1]),
            "kind": worst[2],
            "delta_e": round(worst[3], 1),
        },
        "cvd_ok": worst[3] >= CVD_TARGET,
        "cvd_floor_ok": worst[3] >= CVD_FLOOR,
        "contrast_ok": not contrast_low,
        "contrast_warnings": contrast_low,
        "passed": not lightness_out and not chroma_out and worst[3] >= CVD_TARGET,
    }


def min_adjacent_cvd(colors: list[str]) -> float:
    """Smallest adjacent-pair ΔE across the three CVD simulations."""
    return min(
        delta_e_cvd(a, b, kind)
        for a, b in zip(colors, colors[1:])
        for kind in _CVD_MATRICES
    )
