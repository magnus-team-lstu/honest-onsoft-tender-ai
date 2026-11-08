"""Применить файлы из design/ к запуску Streamlit."""

from __future__ import annotations

import shutil
from pathlib import Path

from design.paths import ROOT_DIR

_SOURCE = Path(__file__).resolve().parent / "streamlit.toml"
_TARGET_DIR = ROOT_DIR / ".streamlit"
_TARGET = _TARGET_DIR / "config.toml"


def sync_streamlit_config() -> Path:
    _TARGET_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_SOURCE, _TARGET)
    return _TARGET
