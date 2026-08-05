from pathlib import Path

from juniper.normalize.pdf import (
    extract_tariff_section,
    extract_text,
    normalize_pdf_text,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _tariff_hash_input(name: str) -> str:
    pdf_bytes = (FIXTURES / name).read_bytes()
    return normalize_pdf_text(extract_tariff_section(extract_text(pdf_bytes)))


def test_extract_text_returns_real_content():
    text = extract_text((FIXTURES / "eei_v1.pdf").read_bytes())
    assert "LARGE LOAD TARIFFS" in text
    assert "Docket 54321" in text


def test_extract_tariff_section_starts_at_marker():
    text = extract_text((FIXTURES / "eei_v1.pdf").read_bytes())
    section = extract_tariff_section(text)
    assert section.startswith("LARGE LOAD TARIFFS")
    assert "AEP Ohio" not in section


def test_extract_tariff_section_falls_back_when_marker_missing():
    section = extract_tariff_section("just some unrelated text, no marker here")
    assert section == "just some unrelated text, no marker here"


def test_projects_only_change_does_not_affect_tariff_hash():
    v1 = _tariff_hash_input("eei_v1.pdf")
    v3 = _tariff_hash_input("eei_v3_projects_changed_tariff_same.pdf")
    assert v1 == v3


def test_real_tariff_change_produces_different_text():
    v1 = _tariff_hash_input("eei_v1.pdf")
    v2 = _tariff_hash_input("eei_v2_tariff_changed.pdf")
    assert v1 != v2
