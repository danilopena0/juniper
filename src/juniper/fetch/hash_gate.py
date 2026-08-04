import sqlite3

from juniper.normalize.html import hash_normalized, normalize_html


def check_for_change(
    conn: sqlite3.Connection,
    source_id: int,
    html: str,
    fetched_at: str,
    raw_path: str,
    url: str | None = None,
) -> bool:
    new_hash = hash_normalized(normalize_html(html))

    row = conn.execute(
        "SELECT norm_hash FROM fetches WHERE source_id = ? ORDER BY id DESC LIMIT 1",
        (source_id,),
    ).fetchone()
    prev_hash = row[0] if row else None
    changed = prev_hash != new_hash

    conn.execute(
        "INSERT INTO fetches (source_id, fetched_at, http_status, raw_path, norm_hash) "
        "VALUES (?, ?, ?, ?, ?)",
        (source_id, fetched_at, 200, raw_path, new_hash),
    )

    if changed:
        diff_summary = f"Page content changed — {url}" if url else "content changed"
        conn.execute(
            """
            INSERT INTO changes
                (source_id, detected_at, prev_hash, new_hash, diff_summary)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source_id, fetched_at, prev_hash, new_hash, diff_summary),
        )

    conn.commit()
    return changed
