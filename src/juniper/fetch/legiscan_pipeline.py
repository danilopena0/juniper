import hashlib
import json
import os
import sqlite3
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

from juniper.fetch import legiscan
from juniper.fetch.db import get_source_id, init_db, sync_sources
from juniper.fetch.legiscan import BillResult
from juniper.fetch.sources import Fetcher, load_sources

SearchFn = Callable[[httpx.Client, str, str, str], dict]

DEFAULT_DB_PATH = Path("data/juniper.db")
DEFAULT_SOURCES_PATH = Path("sources.yaml")
DEFAULT_RAW_DIR = Path("data/raw/legiscan")


def _state_hash(bills: dict[int, str]) -> str:
    pairs = (f"{bid}:{chash}" for bid, chash in sorted(bills.items()))
    return hashlib.sha256("|".join(pairs).encode()).hexdigest()


def _fetch_state_bills(
    client: httpx.Client, state: str, api_key: str, search_fn: SearchFn
) -> tuple[dict[int, BillResult], dict[int, dict]]:
    merged: dict[int, BillResult] = {}
    merged_raw: dict[int, dict] = {}
    for keyword in legiscan.KEYWORDS:
        raw = search_fn(client, state, api_key, keyword)
        for bill in legiscan.parse_search_results(raw):
            merged[bill.bill_id] = bill
        for key, value in raw.get("searchresult", {}).items():
            if key != "summary":
                merged_raw[value["bill_id"]] = value
    return merged, merged_raw


def _process_state(
    conn: sqlite3.Connection,
    raw_dir: Path,
    state: str,
    merged: dict[int, BillResult],
    merged_raw: dict[int, dict],
) -> None:
    fetched_at = datetime.now(UTC).isoformat()

    state_dir = raw_dir / state
    state_dir.mkdir(parents=True, exist_ok=True)
    raw_path = state_dir / f"{fetched_at.replace(':', '-')}.json"
    ordered_raw = [merged_raw[bid] for bid in sorted(merged_raw)]
    raw_path.write_text(json.dumps(ordered_raw, indent=2))

    source_id = get_source_id(
        conn,
        state=state,
        domain="legislation",
        fetcher="legiscan",
        url="https://api.legiscan.com/",
    )
    conn.execute(
        "INSERT INTO fetches (source_id, fetched_at, http_status, raw_path, norm_hash) "
        "VALUES (?, ?, ?, ?, ?)",
        (source_id, fetched_at, 200, str(raw_path), None),
    )

    existing = dict(
        conn.execute(
            "SELECT bill_id, change_hash FROM legiscan_bills WHERE state = ?", (state,)
        ).fetchall()
    )
    relevant_prev = {bid: existing.get(bid, "") for bid in merged}
    relevant_new = {bid: bill.change_hash for bid, bill in merged.items()}
    prev_hash = _state_hash(relevant_prev)
    new_hash = _state_hash(relevant_new)

    changed = [
        bill for bid, bill in merged.items() if existing.get(bid) != bill.change_hash
    ]
    for bill in merged.values():
        conn.execute(
            """
            INSERT INTO legiscan_bills
                (bill_id, state, change_hash, title, url, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (bill_id) DO UPDATE SET
                change_hash = excluded.change_hash,
                title = excluded.title,
                url = excluded.url,
                last_seen_at = excluded.last_seen_at
            """,
            (bill.bill_id, state, bill.change_hash, bill.title, bill.url, fetched_at),
        )

    if changed:
        entries = sorted(changed, key=lambda bill: bill.bill_number)
        # Bill titles can legitimately contain "; " (e.g. "Statewide assessment;
        # testing window; revisions"), so join on newlines instead -- a separator
        # LegiScan titles won't naturally contain, unlike "; ".
        diff_summary = "\n".join(
            f"{bill.bill_number}: {bill.title} — {bill.url}" for bill in entries
        )
        conn.execute(
            """
            INSERT INTO changes
                (source_id, detected_at, prev_hash, new_hash, diff_summary)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source_id, fetched_at, prev_hash, new_hash, diff_summary),
        )

    conn.commit()


def run(
    db_path: Path = DEFAULT_DB_PATH,
    sources_path: Path = DEFAULT_SOURCES_PATH,
    raw_dir: Path = DEFAULT_RAW_DIR,
    api_key: str = "",
    search_fn: SearchFn = legiscan.search_state,
) -> None:
    sources = load_sources(sources_path)
    conn = init_db(db_path)
    sync_sources(conn, sources)

    legiscan_states = [
        s.state for s in sources if s.fetcher == Fetcher.LEGISCAN and s.active
    ]

    with httpx.Client() as client:
        for state in legiscan_states:
            try:
                merged, merged_raw = _fetch_state_bills(
                    client, state, api_key, search_fn
                )
            except httpx.HTTPError as exc:
                msg = f"legiscan: {state} fetch failed, skipping: {exc}"
                print(msg, file=sys.stderr)
                continue
            _process_state(conn, raw_dir, state, merged, merged_raw)

    conn.close()


if __name__ == "__main__":
    run(api_key=os.environ["LEGISCAN_API_KEY"])
