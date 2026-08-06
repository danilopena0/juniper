from pathlib import Path

from juniper.fetch.db import get_source_id, init_db, sync_sources
from juniper.fetch.hash_gate import check_for_change, record_change, record_hash
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


def _eei_source_id(conn):
    sources = load_sources(REPO_ROOT / "sources.yaml")
    sync_sources(conn, sources)
    return get_source_id(
        conn,
        state=None,
        domain="tariff",
        fetcher="eei_pdf",
        url="https://www.eei.org/-/media/Project/EEI/Documents/"
        "Issues%20and%20Policy/List%20of%20Large%20Customer%20Projects%20and%20Tariffs",
    )


def test_record_change_works_with_arbitrary_pre_normalized_text(tmp_path):
    conn = init_db(tmp_path / "test.db")
    source_id = _eei_source_id(conn)

    changed = record_change(
        conn,
        source_id,
        "already normalized plain text, no html involved",
        "2026-08-01T00:00:00",
        "raw/v1.pdf",
        url="https://example.com/report.pdf",
        label="Document",
    )

    assert changed is True
    diff_summary = conn.execute("SELECT diff_summary FROM changes").fetchone()[0]
    assert diff_summary == "Document content changed — https://example.com/report.pdf"

    changed_again = record_change(
        conn,
        source_id,
        "already normalized plain text, no html involved",
        "2026-08-08T00:00:00",
        "raw/v2.pdf",
        url="https://example.com/report.pdf",
        label="Document",
    )
    assert changed_again is False


def _delta_source_id(conn):
    sources = load_sources(REPO_ROOT / "sources.yaml")
    sync_sources(conn, sources)
    return get_source_id(
        conn,
        state=None,
        domain="tax_incentive",
        fetcher="delta_db",
        url="https://sepapower.org/large-load-tariffs-database/",
    )


def test_record_hash_works_with_precomputed_hash_no_normalization(tmp_path):
    conn = init_db(tmp_path / "test.db")
    source_id = _delta_source_id(conn)

    changed = record_hash(
        conn,
        source_id,
        "deadbeef" * 8,
        "2026-08-01T00:00:00",
        "raw/export_v1.csv",
        url="https://sepapower.org/large-load-tariffs-database/",
        label="Database",
    )

    assert changed is True
    diff_summary = conn.execute("SELECT diff_summary FROM changes").fetchone()[0]
    assert diff_summary.startswith("Database content changed")

    changed_again = record_hash(
        conn,
        source_id,
        "deadbeef" * 8,
        "2026-08-08T00:00:00",
        "raw/export_v1_again.csv",
        url="https://sepapower.org/large-load-tariffs-database/",
        label="Database",
    )
    assert changed_again is False
