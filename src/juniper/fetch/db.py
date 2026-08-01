import sqlite3
from pathlib import Path

from juniper.fetch.sources import SourceEntry

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT,
    domain TEXT NOT NULL,
    url TEXT,
    fetcher TEXT NOT NULL,
    selector TEXT,
    active INTEGER NOT NULL,
    UNIQUE (state, domain, fetcher, url)
);

CREATE TABLE IF NOT EXISTS fetches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources (id),
    fetched_at TEXT NOT NULL,
    http_status INTEGER,
    raw_path TEXT,
    norm_hash TEXT
);

CREATE TABLE IF NOT EXISTS changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources (id),
    detected_at TEXT NOT NULL,
    prev_hash TEXT,
    new_hash TEXT,
    diff_summary TEXT
);

CREATE TABLE IF NOT EXISTS legiscan_bills (
    bill_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL,
    change_hash TEXT NOT NULL,
    title TEXT,
    url TEXT,
    last_seen_at TEXT NOT NULL
);
"""


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


_FIND_SOURCE_SQL = (
    "SELECT id FROM sources "
    "WHERE state IS ? AND domain = ? AND fetcher = ? AND url IS ?"
)


def sync_sources(conn: sqlite3.Connection, sources: list[SourceEntry]) -> None:
    # SQLite treats every NULL as distinct under UNIQUE/ON CONFLICT, which breaks
    # dedup for the national sources (state IS NULL) and unconfigured urls
    # (url IS NULL) — so match manually with IS instead of relying on ON CONFLICT.
    for s in sources:
        existing = conn.execute(
            _FIND_SOURCE_SQL, (s.state, s.domain.value, s.fetcher.value, s.url)
        ).fetchone()
        if existing is None:
            values = (
                s.state,
                s.domain.value,
                s.url,
                s.fetcher.value,
                s.selector,
                int(s.active),
            )
            conn.execute(
                "INSERT INTO sources (state, domain, url, fetcher, selector, active) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                values,
            )
        else:
            conn.execute(
                "UPDATE sources SET selector = ?, active = ? WHERE id = ?",
                (s.selector, int(s.active), existing[0]),
            )
    conn.commit()


def get_source_id(
    conn: sqlite3.Connection,
    *,
    state: str | None,
    domain: str,
    fetcher: str,
    url: str | None,
) -> int:
    row = conn.execute(_FIND_SOURCE_SQL, (state, domain, fetcher, url)).fetchone()
    if row is None:
        raise LookupError(f"no source found for {state=} {domain=} {fetcher=} {url=}")
    return row[0]
