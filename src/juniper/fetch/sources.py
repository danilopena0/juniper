from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class Domain(StrEnum):
    LEGISLATION = "legislation"
    TARIFF = "tariff"
    TAX_INCENTIVE = "tax_incentive"
    WATER_SITING = "water_siting"
    MORATORIUM = "moratorium"


class Fetcher(StrEnum):
    LEGISCAN = "legiscan"
    PUC_RSS = "puc_rss"
    EEI_PDF = "eei_pdf"
    DELTA_DB = "delta_db"


class SourceEntry(BaseModel):
    state: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    domain: Domain
    url: str | None = None
    fetcher: Fetcher
    selector: str | None = None
    active: bool = True

    @model_validator(mode="after")
    def check_active_has_url(self) -> "SourceEntry":
        has_http_url = self.url and self.url.startswith(("http://", "https://"))
        if self.active and not has_http_url:
            raise ValueError("active sources must have an http(s) url")
        return self


class SourcesConfig(BaseModel):
    sources: list[SourceEntry]


def load_sources(path: Path) -> list[SourceEntry]:
    data = yaml.safe_load(path.read_text())
    return SourcesConfig.model_validate(data).sources
