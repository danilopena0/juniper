import time

import httpx

from juniper.fetch.legiscan import USER_AGENT
from juniper.fetch.robots import RobotsDisallowedError, is_allowed

MIN_SECONDS_BETWEEN_REQUESTS = 1.0


def fetch_pdf(client: httpx.Client, url: str) -> tuple[bytes, int]:
    if not is_allowed(client, url):
        raise RobotsDisallowedError(f"robots.txt disallows fetching {url}")

    response = client.get(url, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    time.sleep(MIN_SECONDS_BETWEEN_REQUESTS)
    return response.content, response.status_code
