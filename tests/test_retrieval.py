from __future__ import annotations

from src.loader import Package
from src.retrieval import SHORT_PACKAGE, build_context, split_sections


def test_sections_split_on_numbered_headings() -> None:
    chunks = split_sections("01_izveshchenie.txt", "вступление\n1. первый\n2.1. второй")
    assert [text for _name, text in chunks] == ["вступление", "1. первый", "2.1. второй"]


def test_changes_file_stays_whole() -> None:
    chunks = split_sections("05_izmeneniya_izveshcheniya.txt", "1. один\n2. два")
    assert len(chunks) == 1
    assert "1. один" in chunks[0][1]


def test_short_package_is_returned_whole() -> None:
    package = Package("P01", {"01_izveshchenie.txt": "1. цена 18000", "02_trebovaniya_k_zayavke.txt": "срок"})
    context = build_context(package, "какая цена")
    assert "01_izveshchenie.txt" in context
    assert "02_trebovaniya_k_zayavke.txt" in context
    assert len(context) < SHORT_PACKAGE


def test_long_package_keeps_changes_and_top_sections() -> None:
    notice = "\n".join(
        f"{number + 1}. MARKER-{number}-END " + ("наполнитель " * 400) for number in range(12)
    )
    notice += "\n20. MARKER-HIT-END обеспечение заявки уникальное"
    package = Package(
        "P09",
        {
            "01_izveshchenie.txt": notice,
            "05_izmeneniya_izveshcheniya.txt": "СРОК-ИЗМЕНЕНИЙ 27.11.2026",
        },
    )
    assert sum(len(text) for text in package.files.values()) > SHORT_PACKAGE
    context = build_context(package, "обеспечение заявки уникальное")
    assert "СРОК-ИЗМЕНЕНИЙ" in context
    assert "MARKER-HIT-END" in context
    assert sum(f"MARKER-{number}-END" in context for number in range(12)) < 12
