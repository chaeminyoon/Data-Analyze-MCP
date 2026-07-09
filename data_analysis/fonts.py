"""Matplotlib font configuration for Korean text.

Imported for its side effects; configures the default font family per OS and
disables the broken unicode minus sign.
"""
import platform

import matplotlib.pyplot as plt
from matplotlib import rc

_FONTS = {
    "Windows": "Malgun Gothic",
    "Darwin": "AppleGothic",
}


def configure() -> None:
    """Apply the platform-appropriate Korean font settings."""
    family = _FONTS.get(platform.system(), "NanumGothic")
    rc("font", family=family)
    plt.rcParams["axes.unicode_minus"] = False


configure()
