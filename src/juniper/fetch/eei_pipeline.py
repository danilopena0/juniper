import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

from juniper.fetch.db import get_source_id, init_db, sync_sources
from juniper.fetch.hash_gate import record_change
from juniper.fetch.pdf_fetcher import fetch_pdf
from juniper.fetch.robots import RobotsDisallowedError
from juniper.fetch.sources import Fetcher, load_sources
from juniper.normalize.pdf import (
    extract_tariff_section,
    extract_text,
    normalize_pdf_text,
)

FetchFn = Callable[[httpx.Client, str], tuple[bytes, int]]

DEFAULT_DB_PATH = Path("data/juniper.db")
DEFAULT_SOURCES_PATH = Path("sources.yaml")
DEFAULT_RAW_DIR = Path("data/raw/eei_pdf")


def run(
    db_path: Path = DEFAULT_DB_PATH,
    sources_path: Path = DEFAULT_SOURCES_PATH,
    raw_dir: Path = DEFAULT_RAW_DIR,
    fetch_fn: FetchFn = fetch_pdf,
) -> None:
    sources = load_sources(sources_path)
    conn = init_db(db_path)
    sync_sources(conn, sources)

    eei_sources = [
        s for s in sources if s.fetcher == Fetcher.EEI_PDF and s.active
    ]

    with httpx.Client() as client:
        for source in eei_sources:
            try:
                pdf_bytes, _status = fetch_fn(client, source.url)
            except RobotsDisallowedError as exc:
                msg = f"eei_pdf: disallowed by robots.txt, skipping: {exc}"
                print(msg, file=sys.stderr)
                continue
            except httpx.HTTPError as exc:
                print(f"eei_pdf: fetch failed, skipping: {exc}", file=sys.stderr)
                continue

            fetched_at = datetime.now(UTC).isoformat()
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_path = raw_dir / f"{fetched_at.replace(':', '-')}.pdf"
            raw_path.write_bytes(pdf_bytes)

            tariff_text = extract_tariff_section(extract_text(pdf_bytes))
            normalized = normalize_pdf_text(tariff_text)

            source_id = get_source_id(
                conn,
                state=source.state,
                domain=source.domain.value,
                fetcher=source.fetcher.value,
                url=source.url,
            )
            record_change(
                conn,
                source_id,
                normalized,
                fetched_at,
                str(raw_path),
                url=source.url,
                label="Document",
            )

    conn.close()


if __name__ == "__main__":
    run()
