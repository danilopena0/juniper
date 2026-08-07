import hashlib
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from juniper.fetch.db import get_source_id, init_db, sync_sources
from juniper.fetch.hash_gate import record_hash
from juniper.fetch.sources import Fetcher, load_sources

DEFAULT_DB_PATH = Path("data/juniper.db")
DEFAULT_SOURCES_PATH = Path("sources.yaml")
DEFAULT_MANUAL_DIR = Path("data/manual/delta_db")
DEFAULT_RAW_DIR = Path("data/raw/delta_db")


def _latest_manual_file(manual_dir: Path) -> Path | None:
    candidates = [
        p
        for p in manual_dir.iterdir()
        if p.is_file()
        and not p.name.startswith(".")
        and not p.name.lower().startswith("readme")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def run(
    db_path: Path = DEFAULT_DB_PATH,
    sources_path: Path = DEFAULT_SOURCES_PATH,
    manual_dir: Path = DEFAULT_MANUAL_DIR,
    raw_dir: Path = DEFAULT_RAW_DIR,
) -> None:
    sources = load_sources(sources_path)
    conn = init_db(db_path)
    sync_sources(conn, sources)

    delta_sources = [s for s in sources if s.fetcher == Fetcher.DELTA_DB and s.active]

    latest_file = _latest_manual_file(manual_dir) if manual_dir.exists() else None
    if latest_file is None:
        print(
            f"delta_db: no manual export found in {manual_dir}, skipping",
            file=sys.stderr,
        )
        conn.close()
        return

    file_bytes = latest_file.read_bytes()
    new_hash = hashlib.sha256(file_bytes).hexdigest()
    fetched_at = datetime.now(UTC).isoformat()

    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{fetched_at.replace(':', '-')}-{latest_file.name}"
    shutil.copyfile(latest_file, raw_path)

    for source in delta_sources:
        source_id = get_source_id(
            conn,
            state=source.state,
            domain=source.domain.value,
            fetcher=source.fetcher.value,
            url=source.url,
        )
        record_hash(
            conn,
            source_id,
            new_hash,
            fetched_at,
            str(raw_path),
            url=source.url,
            label="Database",
        )

    conn.close()


if __name__ == "__main__":
    run()
