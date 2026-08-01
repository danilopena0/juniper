from pathlib import Path

import pytest
from pydantic import ValidationError

from juniper.fetch.sources import (
    Domain,
    Fetcher,
    SourceEntry,
    SourcesConfig,
    load_sources,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_valid_config_loads():
    config = SourcesConfig.model_validate(
        {
            "sources": [
                {
                    "state": "TX",
                    "domain": "legislation",
                    "fetcher": "legiscan",
                    "url": "https://api.legiscan.com/",
                    "active": True,
                },
                {
                    "state": None,
                    "domain": "tariff",
                    "fetcher": "eei_pdf",
                    "url": None,
                    "active": False,
                },
                {
                    "state": "OH",
                    "domain": "tariff",
                    "fetcher": "puc_rss",
                    "url": None,
                    "active": False,
                },
                {
                    "state": None,
                    "domain": "tax_incentive",
                    "fetcher": "delta_db",
                    "url": None,
                    "active": False,
                },
            ]
        }
    )
    assert len(config.sources) == 4
    assert config.sources[0].domain is Domain.LEGISLATION
    assert config.sources[0].fetcher is Fetcher.LEGISCAN


def test_active_without_url_rejected():
    with pytest.raises(ValidationError):
        SourceEntry(
            state="TX",
            domain=Domain.LEGISLATION,
            fetcher=Fetcher.LEGISCAN,
            active=True,
        )


def test_bad_domain_rejected():
    with pytest.raises(ValidationError):
        SourceEntry.model_validate(
            {
                "state": "TX",
                "domain": "not_a_domain",
                "fetcher": "legiscan",
                "active": False,
            }
        )


def test_bad_fetcher_rejected():
    with pytest.raises(ValidationError):
        SourceEntry.model_validate(
            {
                "state": "TX",
                "domain": "legislation",
                "fetcher": "not_a_fetcher",
                "active": False,
            }
        )


def test_bad_state_format_rejected():
    with pytest.raises(ValidationError):
        SourceEntry.model_validate(
            {
                "state": "Texas",
                "domain": "legislation",
                "fetcher": "legiscan",
                "active": False,
            }
        )


def test_repo_sources_yaml_is_valid():
    sources = load_sources(REPO_ROOT / "sources.yaml")
    assert len(sources) == 12
    states = {s.state for s in sources if s.state is not None}
    assert states == {"TX", "VA", "OH", "GA", "AZ"}
