import sqlite3
from pathlib import Path

from juniper.fetch.html_fetcher import RobotsDisallowedError
from juniper.fetch.puc_rss_pipeline import run

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent

TX_URL = "https://puc.texas.gov/agency/resources/pubs/news/"
GA_URL = "https://psc.ga.gov/newsroom/newsreleases/"
AZ_URL = "https://azcc.gov/news"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def _fake_fetch(
    html_by_url: dict[str, str], raise_disallowed_for: set[str] = frozenset()
):
    def fetch_fn(client, url):
        if url in raise_disallowed_for:
            raise RobotsDisallowedError(f"robots.txt disallows {url}")
        return html_by_url[url], 200

    return fetch_fn


def test_first_run_records_a_change_per_active_state(tmp_path):
    db_path = tmp_path / "juniper.db"
    raw_dir = tmp_path / "raw"

    html_by_url = {
        TX_URL: _fixture("puc_page_v1.html"),
        GA_URL: _fixture("puc_page_v1.html"),
        AZ_URL: _fixture("puc_page_v1.html"),
    }

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        fetch_fn=_fake_fetch(html_by_url),
    )

    conn = sqlite3.connect(db_path)
    changes = conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0]
    assert changes == 3

    fetches = conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0]
    assert fetches == 3

    for state in ("TX", "GA", "AZ"):
        raw_files = list((raw_dir / state).glob("*.html"))
        assert len(raw_files) == 1


def test_cosmetic_refetch_is_not_a_change(tmp_path):
    db_path = tmp_path / "juniper.db"
    raw_dir = tmp_path / "raw"

    v1_by_url = {
        TX_URL: _fixture("puc_page_v1.html"),
        GA_URL: _fixture("puc_page_v1.html"),
        AZ_URL: _fixture("puc_page_v1.html"),
    }
    v2_by_url = {
        TX_URL: _fixture("puc_page_v2_cosmetic.html"),
        GA_URL: _fixture("puc_page_v2_cosmetic.html"),
        AZ_URL: _fixture("puc_page_v2_cosmetic.html"),
    }

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        fetch_fn=_fake_fetch(v1_by_url),
    )
    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        fetch_fn=_fake_fetch(v2_by_url),
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0] == 6


def test_real_change_is_detected_for_one_state_only(tmp_path):
    db_path = tmp_path / "juniper.db"
    raw_dir = tmp_path / "raw"

    v1_by_url = {
        TX_URL: _fixture("puc_page_v1.html"),
        GA_URL: _fixture("puc_page_v1.html"),
        AZ_URL: _fixture("puc_page_v1.html"),
    }
    tx_changed_by_url = {
        TX_URL: _fixture("puc_page_v3_real_change.html"),
        GA_URL: _fixture("puc_page_v1.html"),
        AZ_URL: _fixture("puc_page_v1.html"),
    }

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        fetch_fn=_fake_fetch(v1_by_url),
    )
    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        fetch_fn=_fake_fetch(tx_changed_by_url),
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 4

    diff_summaries = [
        row[0] for row in conn.execute("SELECT diff_summary FROM changes ORDER BY id")
    ]
    assert TX_URL in diff_summaries[-1]


def test_robots_disallowed_for_one_state_does_not_stop_others(tmp_path):
    db_path = tmp_path / "juniper.db"
    raw_dir = tmp_path / "raw"

    html_by_url = {
        GA_URL: _fixture("puc_page_v1.html"),
        AZ_URL: _fixture("puc_page_v1.html"),
    }

    run(
        db_path=db_path,
        sources_path=REPO_ROOT / "sources.yaml",
        raw_dir=raw_dir,
        fetch_fn=_fake_fetch(html_by_url, raise_disallowed_for={TX_URL}),
    )

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 2
    assert list((raw_dir / "TX").glob("*.html")) == []
    assert len(list((raw_dir / "GA").glob("*.html"))) == 1
    assert len(list((raw_dir / "AZ").glob("*.html"))) == 1
