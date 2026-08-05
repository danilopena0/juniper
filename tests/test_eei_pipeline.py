import sqlite3
from pathlib import Path

from juniper.fetch.eei_pipeline import run
from juniper.fetch.robots import RobotsDisallowedError

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent

EEI_URL = (
    "https://www.eei.org/-/media/Project/EEI/Documents/Issues%20and%20Policy/"
    "List%20of%20Large%20Customer%20Projects%20and%20Tariffs"
)


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fake_fetch(pdf_bytes: bytes, raise_disallowed: bool = False):
    def fetch_fn(client, url):
        if raise_disallowed:
            raise RobotsDisallowedError(f"robots.txt disallows {url}")
        return pdf_bytes, 200

    return fetch_fn


def test_first_run_records_a_change(tmp_path):
    db_path = tmp_path / "juniper.db"
    raw_dir = tmp_path / "raw"

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        fetch_fn=_fake_fetch(_fixture_bytes("eei_v1.pdf")),
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0] == 1

    raw_files = list(raw_dir.glob("*.pdf"))
    assert len(raw_files) == 1

    diff_summary = conn.execute("SELECT diff_summary FROM changes").fetchone()[0]
    assert EEI_URL in diff_summary
    assert diff_summary.startswith("Document content changed")


def test_projects_only_change_does_not_trigger_a_new_change_row(tmp_path):
    db_path = tmp_path / "juniper.db"
    raw_dir = tmp_path / "raw"

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        fetch_fn=_fake_fetch(_fixture_bytes("eei_v1.pdf")),
    )
    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        fetch_fn=_fake_fetch(_fixture_bytes("eei_v3_projects_changed_tariff_same.pdf")),
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0] == 2


def test_real_tariff_change_triggers_a_new_change_row(tmp_path):
    db_path = tmp_path / "juniper.db"
    raw_dir = tmp_path / "raw"

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        fetch_fn=_fake_fetch(_fixture_bytes("eei_v1.pdf")),
    )
    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        fetch_fn=_fake_fetch(_fixture_bytes("eei_v2_tariff_changed.pdf")),
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 2


def test_robots_disallowed_degrades_gracefully(tmp_path):
    db_path = tmp_path / "juniper.db"
    raw_dir = tmp_path / "raw"

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        fetch_fn=_fake_fetch(_fixture_bytes("eei_v1.pdf"), raise_disallowed=True),
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0] == 0
    assert not raw_dir.exists() or list(raw_dir.glob("*.pdf")) == []
