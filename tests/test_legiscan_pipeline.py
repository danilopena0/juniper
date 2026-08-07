import json
from pathlib import Path

from juniper.fetch.legiscan_pipeline import run

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent

EMPTY_RESULT = {"status": "OK", "searchresult": {"summary": {}}}


def _fake_search(fixture_name):
    raw = json.loads((FIXTURES / fixture_name).read_text())

    def search_fn(client, state, api_key, keyword):
        return raw if state == "TX" else EMPTY_RESULT

    return search_fn


def test_first_run_records_all_bills_as_changed(tmp_path):
    db_path = tmp_path / "juniper.db"
    raw_dir = tmp_path / "raw"

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        api_key="test-key",
        search_fn=_fake_search("legiscan_search_tx.json"),
    )

    import sqlite3

    conn = sqlite3.connect(db_path)
    changes = conn.execute("SELECT diff_summary FROM changes").fetchall()
    assert len(changes) == 1
    diff_summary = changes[0][0]
    assert diff_summary.startswith("HB1234: ")
    assert "https://legiscan.com/TX/bill/HB1234/2026" in diff_summary
    assert "SB45: " in diff_summary
    assert "https://legiscan.com/TX/bill/SB45/2026" in diff_summary

    bills = conn.execute("SELECT bill_id, change_hash FROM legiscan_bills").fetchall()
    assert len(bills) == 2

    raw_files = list((raw_dir / "TX").glob("*.json"))
    assert len(raw_files) == 1


def test_second_run_only_records_changed_bill(tmp_path):
    db_path = tmp_path / "juniper.db"
    raw_dir = tmp_path / "raw"

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        api_key="test-key",
        search_fn=_fake_search("legiscan_search_tx.json"),
    )
    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        api_key="test-key",
        search_fn=_fake_search("legiscan_search_tx_changed.json"),
    )

    import sqlite3

    conn = sqlite3.connect(db_path)
    changes = conn.execute(
        "SELECT diff_summary FROM changes ORDER BY id"
    ).fetchall()
    assert len(changes) == 2
    second_diff_summary = changes[1][0]
    assert second_diff_summary.startswith("SB45: ")
    assert "HB1234" not in second_diff_summary


def test_bill_title_containing_semicolons_is_not_split(tmp_path):
    db_path = tmp_path / "juniper.db"
    raw_dir = tmp_path / "raw"

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        api_key="test-key",
        search_fn=_fake_search("legiscan_search_tx_semicolon_title.json"),
    )

    import sqlite3

    conn = sqlite3.connect(db_path)
    diff_summary = conn.execute("SELECT diff_summary FROM changes").fetchone()[0]
    entries = diff_summary.split("\n")
    assert len(entries) == 2
    assert "HB2032: Statewide assessment; testing window; revisions — " in diff_summary
