from pathlib import Path

from juniper.normalize.html import hash_normalized, normalize_html

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _hash_fixture(name: str) -> str:
    html = (FIXTURES / name).read_text()
    return hash_normalized(normalize_html(html))


def test_cosmetic_changes_hash_identically():
    v1_hash = _hash_fixture("puc_page_v1.html")
    v2_hash = _hash_fixture("puc_page_v2_cosmetic.html")
    assert v1_hash == v2_hash


def test_real_content_change_hashes_differently():
    v1_hash = _hash_fixture("puc_page_v1.html")
    v3_hash = _hash_fixture("puc_page_v3_real_change.html")
    assert v1_hash != v3_hash


def test_script_and_nav_content_excluded():
    html = (FIXTURES / "puc_page_v1.html").read_text()
    normalized = normalize_html(html)
    assert "analytics.example.com" not in normalized
    assert "Home" not in normalized
    assert "csrf_token" not in normalized
    assert "Docket 54321" in normalized
