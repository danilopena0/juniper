from pathlib import Path

from juniper.fetch.db import (
    get_last_digest_at,
    get_source_id,
    init_db,
    record_digest_run,
    sync_sources,
)
from juniper.fetch.sources import load_sources
from juniper.render.digest import render_digest

REPO_ROOT = Path(__file__).resolve().parent.parent
STATES = ["AZ", "GA", "OH", "TX", "VA"]


def _seed(conn, tmp_path):
    sources = load_sources(REPO_ROOT / "sources.yaml")
    sync_sources(conn, sources)
    tx_source_id = get_source_id(
        conn, state="TX", domain="legislation", fetcher="legiscan", url="https://api.legiscan.com/"
    )
    conn.execute(
        """
        INSERT INTO changes (source_id, detected_at, prev_hash, new_hash, diff_summary)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            tx_source_id,
            "2026-08-01T00:00:00",
            "old",
            "new",
            "HB1234: Relating to data centers. — https://legiscan.com/TX/bill/HB1234/2026",
        ),
    )
    conn.commit()
    return tx_source_id


def test_first_render_shows_seeded_change_and_no_changes_elsewhere(tmp_path):
    conn = init_db(tmp_path / "test.db")
    _seed(conn, tmp_path)

    digest = render_digest(conn, STATES, since=None, now="2026-08-08T00:00:00")

    assert "## TX" in digest
    assert "HB1234: Relating to data centers." in digest
    assert "https://legiscan.com/TX/bill/HB1234/2026" in digest
    assert "## VA\n_No changes this period._" in digest
    for state in STATES:
        assert f"## {state}" in digest


def test_second_render_with_no_new_changes_shows_nothing(tmp_path):
    conn = init_db(tmp_path / "test.db")
    _seed(conn, tmp_path)

    render_digest(conn, STATES, since=None, now="2026-08-08T00:00:00")
    record_digest_run(conn, "2026-08-08T00:00:00")

    since = get_last_digest_at(conn)
    digest = render_digest(conn, STATES, since=since, now="2026-08-15T00:00:00")

    assert "HB1234" not in digest
    assert "## TX\n_No changes this period._" in digest


def test_change_after_last_render_appears_only_once(tmp_path):
    conn = init_db(tmp_path / "test.db")
    tx_source_id = _seed(conn, tmp_path)

    render_digest(conn, STATES, since=None, now="2026-08-08T00:00:00")
    record_digest_run(conn, "2026-08-08T00:00:00")

    conn.execute(
        """
        INSERT INTO changes (source_id, detected_at, prev_hash, new_hash, diff_summary)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            tx_source_id,
            "2026-08-10T00:00:00",
            "new",
            "newer",
            "SB45: Relating to large loads. — https://legiscan.com/TX/bill/SB45/2026",
        ),
    )
    conn.commit()

    since = get_last_digest_at(conn)
    second_digest = render_digest(conn, STATES, since=since, now="2026-08-15T00:00:00")
    record_digest_run(conn, "2026-08-15T00:00:00")

    assert "SB45" in second_digest
    assert "HB1234" not in second_digest

    since = get_last_digest_at(conn)
    third_digest = render_digest(conn, STATES, since=since, now="2026-08-22T00:00:00")
    assert "SB45" not in third_digest
    assert "## TX\n_No changes this period._" in third_digest


def test_mixed_lanes_both_appear_labeled_under_same_state(tmp_path):
    conn = init_db(tmp_path / "test.db")
    _seed(conn, tmp_path)
    tx_puc_id = get_source_id(
        conn,
        state="TX",
        domain="tariff",
        fetcher="puc_rss",
        url="https://puc.texas.gov/agency/resources/pubs/news/",
    )
    conn.execute(
        """
        INSERT INTO changes (source_id, detected_at, prev_hash, new_hash, diff_summary)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            tx_puc_id,
            "2026-08-02T00:00:00",
            "old",
            "new",
            "Page content changed — https://puc.texas.gov/agency/resources/pubs/news/",
        ),
    )
    conn.commit()

    digest = render_digest(conn, STATES, since=None, now="2026-08-08T00:00:00")

    assert "- [Legislation] HB1234:" in digest
    assert "- [PUC Tariff] Page content changed" in digest
