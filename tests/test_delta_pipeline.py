import shutil
import sqlite3
from pathlib import Path

from juniper.fetch.delta_pipeline import run

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent


def test_first_run_with_manual_file_records_a_change(tmp_path):
    db_path = tmp_path / "juniper.db"
    manual_dir = tmp_path / "manual"
    raw_dir = tmp_path / "raw"
    manual_dir.mkdir()
    shutil.copy(FIXTURES / "delta_export_v1.csv", manual_dir / "export.csv")

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        manual_dir=manual_dir,
        raw_dir=raw_dir,
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0] == 1
    assert len(list(raw_dir.glob("*export.csv"))) == 1


def test_unchanged_file_on_second_run_records_no_new_change(tmp_path):
    db_path = tmp_path / "juniper.db"
    manual_dir = tmp_path / "manual"
    raw_dir = tmp_path / "raw"
    manual_dir.mkdir()
    shutil.copy(FIXTURES / "delta_export_v1.csv", manual_dir / "export.csv")

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        manual_dir=manual_dir,
        raw_dir=raw_dir,
    )
    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        manual_dir=manual_dir,
        raw_dir=raw_dir,
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0] == 2


def test_replaced_file_on_second_run_records_a_new_change(tmp_path):
    db_path = tmp_path / "juniper.db"
    manual_dir = tmp_path / "manual"
    raw_dir = tmp_path / "raw"
    manual_dir.mkdir()
    shutil.copy(FIXTURES / "delta_export_v1.csv", manual_dir / "export.csv")

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        manual_dir=manual_dir,
        raw_dir=raw_dir,
    )

    shutil.copy(FIXTURES / "delta_export_v2_changed.csv", manual_dir / "export.csv")
    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        manual_dir=manual_dir,
        raw_dir=raw_dir,
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 2


def test_empty_manual_dir_degrades_gracefully(tmp_path):
    db_path = tmp_path / "juniper.db"
    manual_dir = tmp_path / "manual"
    raw_dir = tmp_path / "raw"
    manual_dir.mkdir()

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        manual_dir=manual_dir,
        raw_dir=raw_dir,
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0] == 0


def test_missing_manual_dir_degrades_gracefully(tmp_path):
    db_path = tmp_path / "juniper.db"
    manual_dir = tmp_path / "manual_does_not_exist"
    raw_dir = tmp_path / "raw"

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        manual_dir=manual_dir,
        raw_dir=raw_dir,
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 0


def test_readme_in_manual_dir_is_not_treated_as_an_export(tmp_path):
    db_path = tmp_path / "juniper.db"
    manual_dir = tmp_path / "manual"
    raw_dir = tmp_path / "raw"
    manual_dir.mkdir()
    (manual_dir / "README.md").write_text("drop your export file here")

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        manual_dir=manual_dir,
        raw_dir=raw_dir,
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0] == 0
