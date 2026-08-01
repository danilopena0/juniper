from pathlib import Path

from juniper.fetch.db import get_source_id, init_db, sync_sources
from juniper.fetch.sources import load_sources

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_init_db_creates_tables(tmp_path):
    conn = init_db(tmp_path / "test.db")
    query = "SELECT name FROM sqlite_master WHERE type = 'table'"
    tables = {row[0] for row in conn.execute(query).fetchall()}
    assert {"sources", "fetches", "changes", "legiscan_bills"} <= tables


def test_sync_sources_upserts_without_duplicating(tmp_path):
    conn = init_db(tmp_path / "test.db")
    sources = load_sources(REPO_ROOT / "sources.yaml")

    sync_sources(conn, sources)
    sync_sources(conn, sources)

    count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    assert count == len(sources)


def test_get_source_id_finds_legiscan_source(tmp_path):
    conn = init_db(tmp_path / "test.db")
    sources = load_sources(REPO_ROOT / "sources.yaml")
    sync_sources(conn, sources)

    source_id = get_source_id(
        conn, state="TX", domain="legislation", fetcher="legiscan", url="https://api.legiscan.com/"
    )
    assert isinstance(source_id, int)
