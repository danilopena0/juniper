import sqlite3
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

from juniper.fetch.db import get_source_id, init_db, sync_sources
from juniper.fetch.hash_gate import check_for_change
from juniper.fetch.html_fetcher import RobotsDisallowedError, fetch_html
from juniper.fetch.sources import Fetcher, load_sources

FetchFn = Callable[[httpx.Client, str], tuple[str, int]]

DEFAULT_DB_PATH = Path("data/juniper.db")
DEFAULT_SOURCES_PATH = Path("sources.yaml")
DEFAULT_RAW_DIR = Path("data/raw/puc_rss")


def _process_state(
    conn: sqlite3.Connection,
    raw_dir: Path,
    state: str,
    url: str,
    html: str,
) -> None:
    fetched_at = datetime.now(UTC).isoformat()

    state_dir = raw_dir / state
    state_dir.mkdir(parents=True, exist_ok=True)
    raw_path = state_dir / f"{fetched_at.replace(':', '-')}.html"
    raw_path.write_text(html)

    source_id = get_source_id(
        conn, state=state, domain="tariff", fetcher="puc_rss", url=url
    )
    check_for_change(conn, source_id, html, fetched_at, str(raw_path), url=url)


def run(
    db_path: Path = DEFAULT_DB_PATH,
    sources_path: Path = DEFAULT_SOURCES_PATH,
    raw_dir: Path = DEFAULT_RAW_DIR,
    fetch_fn: FetchFn = fetch_html,
) -> None:
    sources = load_sources(sources_path)
    conn = init_db(db_path)
    sync_sources(conn, sources)

    puc_rss_sources = [
        (s.state, s.url)
        for s in sources
        if s.fetcher == Fetcher.PUC_RSS and s.active
    ]

    with httpx.Client() as client:
        for state, url in puc_rss_sources:
            try:
                html, _status = fetch_fn(client, url)
            except RobotsDisallowedError as exc:
                msg = f"puc_rss: {state} disallowed by robots.txt, skipping: {exc}"
                print(msg, file=sys.stderr)
                continue
            except httpx.HTTPError as exc:
                msg = f"puc_rss: {state} fetch failed, skipping: {exc}"
                print(msg, file=sys.stderr)
                continue
            _process_state(conn, raw_dir, state, url, html)

    conn.close()


if __name__ == "__main__":
    run()
