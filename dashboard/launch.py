"""Команда `uv run dashboard [a|b|c]` открывает дашборд на этом компьютере."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = Path(__file__).resolve().parent / "app.py"


def main() -> None:
    page = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if page not in {"", "a", "b", "c"}:
        print("Команда: uv run dashboard [a|b|c]", file=sys.stderr)
        raise SystemExit(2)
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        "8501",
        "--browser.gatherUsageStats",
        "false",
        "--server.showEmailPrompt",
        "false",
        "--server.headless",
        "false",
        "--",
    ]
    if page:
        command.append(page)
    raise SystemExit(subprocess.call(command, cwd=ROOT))


if __name__ == "__main__":
    main()
