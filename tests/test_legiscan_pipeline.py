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
    assert changes[0][0] == "HB1234, SB45"

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
    assert changes[1][0] == "SB45"
