from __future__ import annotations

from pathlib import Path

DESIGN_DIR = Path(__file__).resolve().parent
ROOT_DIR = DESIGN_DIR.parent


def assets_dir() -> Path:
    return DESIGN_DIR / "assets"


def logo_path() -> Path:
    return assets_dir() / "logo.jpg"
