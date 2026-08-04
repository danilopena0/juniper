from pathlib import Path

from juniper.fetch.db import get_source_id, init_db, sync_sources
from juniper.fetch.hash_gate import check_for_change
from juniper.fetch.sources import load_sources

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _puc_source_id(conn):
    # OH's puc_rss source is still unconfigured (url=None, active=False) as of
    # this writing — used here only as a stand-in source_id for hash-gate
    # tests, independent of whether it's actually fetchable.
    sources = load_sources(REPO_ROOT / "sources.yaml")
    sync_sources(conn, sources)
    return get_source_id(conn, state="OH", domain="tariff", fetcher="puc_rss", url=None)


def test_first_fetch_is_always_a_change(tmp_path):
    conn = init_db(tmp_path / "test.db")
    source_id = _puc_source_id(conn)
    html = (FIXTURES / "puc_page_v1.html").read_text()

    changed = check_for_change(
        conn, source_id, html, "2026-08-01T00:00:00", "raw/v1.html"
    )

    assert changed is True
    assert conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 1


def test_cosmetic_refetch_is_not_a_change(tmp_path):
    conn = init_db(tmp_path / "test.db")
    source_id = _puc_source_id(conn)
    v1 = (FIXTURES / "puc_page_v1.html").read_text()
    v2 = (FIXTURES / "puc_page_v2_cosmetic.html").read_text()

    check_for_change(conn, source_id, v1, "2026-08-01T00:00:00", "raw/v1.html")
    changed = check_for_change(
        conn, source_id, v2, "2026-08-08T00:00:00", "raw/v2.html"
    )

    assert changed is False
    assert conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 1


def test_real_change_is_detected(tmp_path):
    conn = init_db(tmp_path / "test.db")
    source_id = _puc_source_id(conn)
    v1 = (FIXTURES / "puc_page_v1.html").read_text()
    v3 = (FIXTURES / "puc_page_v3_real_change.html").read_text()

    check_for_change(conn, source_id, v1, "2026-08-01T00:00:00", "raw/v1.html")
    changed = check_for_change(
        conn, source_id, v3, "2026-08-08T00:00:00", "raw/v3.html"
    )

    assert changed is True
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 2


def test_diff_summary_includes_url_when_provided(tmp_path):
    conn = init_db(tmp_path / "test.db")
    source_id = _puc_source_id(conn)
    html = (FIXTURES / "puc_page_v1.html").read_text()

    check_for_change(
        conn,
        source_id,
        html,
        "2026-08-01T00:00:00",
        "raw/v1.html",
        url="https://example.com/news",
    )

    diff_summary = conn.execute("SELECT diff_summary FROM changes").fetchone()[0]
    assert "https://example.com/news" in diff_summary
