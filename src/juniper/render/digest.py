import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from juniper.fetch.db import (
    get_last_digest_at,
    init_db,
    record_digest_run,
    sync_sources,
)
from juniper.fetch.sources import Fetcher, load_sources

DEFAULT_DB_PATH = Path("data/juniper.db")
DEFAULT_SOURCES_PATH = Path("sources.yaml")
DEFAULT_OUTPUT_PATH = Path("digest.md")

LANES = [("legiscan", "Legislation"), ("puc_rss", "PUC Tariff")]
NATIONAL_LANES = [("eei_pdf", "EEI Large-Load Tariffs")]


def _lane_bullets(
    conn: sqlite3.Connection, state: str, fetcher: str, label: str, since: str | None
) -> list[str]:
    if since is None:
        rows = conn.execute(
            """
            SELECT c.diff_summary FROM changes c
            JOIN sources s ON s.id = c.source_id
            WHERE s.state = ? AND s.fetcher = ?
            ORDER BY c.detected_at
            """,
            (state, fetcher),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT c.diff_summary FROM changes c
            JOIN sources s ON s.id = c.source_id
            WHERE s.state = ? AND s.fetcher = ? AND c.detected_at > ?
            ORDER BY c.detected_at
            """,
            (state, fetcher, since),
        ).fetchall()

    bullets = []
    for (diff_summary,) in rows:
        for entry in diff_summary.split("; "):
            bullets.append(f"- [{label}] {entry}")
    return bullets


def _state_section(conn: sqlite3.Connection, state: str, since: str | None) -> str:
    bullets = []
    for fetcher, label in LANES:
        bullets.extend(_lane_bullets(conn, state, fetcher, label, since))

    if not bullets:
        return f"## {state}\n_No changes this period._"
    return f"## {state}\n" + "\n".join(bullets)


def _national_bullets(
    conn: sqlite3.Connection, fetcher: str, label: str, since: str | None
) -> list[str]:
    if since is None:
        rows = conn.execute(
            """
            SELECT c.diff_summary FROM changes c
            JOIN sources s ON s.id = c.source_id
            WHERE s.state IS NULL AND s.fetcher = ?
            ORDER BY c.detected_at
            """,
            (fetcher,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT c.diff_summary FROM changes c
            JOIN sources s ON s.id = c.source_id
            WHERE s.state IS NULL AND s.fetcher = ? AND c.detected_at > ?
            ORDER BY c.detected_at
            """,
            (fetcher, since),
        ).fetchall()

    bullets = []
    for (diff_summary,) in rows:
        for entry in diff_summary.split("; "):
            bullets.append(f"- [{label}] {entry}")
    return bullets


def _national_section(conn: sqlite3.Connection, since: str | None) -> str:
    bullets = []
    for fetcher, label in NATIONAL_LANES:
        bullets.extend(_national_bullets(conn, fetcher, label, since))

    if not bullets:
        return "## National\n_No changes this period._"
    return "## National\n" + "\n".join(bullets)


def render_digest(
    conn: sqlite3.Connection, states: list[str], since: str | None, now: str
) -> str:
    date = now.split("T")[0]
    sections = [_national_section(conn, since)]
    sections.extend(_state_section(conn, state, since) for state in states)
    return f"# RegTracker Digest — {date}\n\n" + "\n\n".join(sections) + "\n"


def run(
    db_path: Path = DEFAULT_DB_PATH,
    sources_path: Path = DEFAULT_SOURCES_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    sources = load_sources(sources_path)
    conn = init_db(db_path)
    sync_sources(conn, sources)

    states = sorted(
        s.state for s in sources if s.fetcher == Fetcher.LEGISCAN and s.active
    )

    since = get_last_digest_at(conn)
    now = datetime.now(UTC).isoformat()

    digest = render_digest(conn, states, since, now)
    output_path.write_text(digest)
    record_digest_run(conn, now)
    conn.close()


if __name__ == "__main__":
    run()
