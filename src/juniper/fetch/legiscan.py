import time

import httpx
from pydantic import BaseModel

API_URL = "https://api.legiscan.com/"
USER_AGENT = "juniper-regtracker/0.1 (contact: danilopena93@gmail.com)"
KEYWORDS = ["data center", "large load", "colocation", "digital infrastructure"]
MIN_SECONDS_BETWEEN_REQUESTS = 1.0


class BillResult(BaseModel):
    bill_id: int
    state: str
    bill_number: str
    title: str
    url: str
    change_hash: str
    last_action: str | None = None
    last_action_date: str | None = None


def search_state(client: httpx.Client, state: str, api_key: str, keyword: str) -> dict:
    response = client.get(
        API_URL,
        params={"key": api_key, "op": "getSearch", "state": state, "query": keyword},
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    time.sleep(MIN_SECONDS_BETWEEN_REQUESTS)
    return response.json()


def parse_search_results(raw: dict) -> list[BillResult]:
    results = raw.get("searchresult", {})
    return [
        BillResult.model_validate(value)
        for key, value in results.items()
        if key != "summary"
    ]
