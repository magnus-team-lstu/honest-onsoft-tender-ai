from __future__ import annotations

from pathlib import Path

from src.loader import load_package, read_text

ROOT = Path(__file__).resolve().parents[1] / "data" / "packages"


def test_empty_file_does_not_crash(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_bytes(b"")
    assert read_text(path) == ("", "пустой файл")


def test_utf8_bom_is_stripped(tmp_path: Path) -> None:
    path = tmp_path / "bom.txt"
    path.write_bytes("цена".encode("utf-8-sig"))
    assert read_text(path) == ("цена", "")


def test_utf16_bom(tmp_path: Path) -> None:
    path = tmp_path / "wide.txt"
    path.write_bytes("цена".encode("utf-16"))
    assert read_text(path) == ("цена", "")


def test_cp1251(tmp_path: Path) -> None:
    path = tmp_path / "win.txt"
    path.write_bytes("цена".encode("cp1251"))
    assert read_text(path) == ("цена", "")


def test_all_training_packages_load() -> None:
    packages = [load_package(path) for path in sorted(ROOT.glob("P*"))]
    assert [package.id for package in packages] == ["P01", "P02", "P03", "P04", "P05", "P06"]
    assert sum(len(package.files) for package in packages) == 26
    assert all(package.reasons == {} for package in packages)
    assert all(text for package in packages for text in package.files.values())
