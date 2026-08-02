import time
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import httpx

from juniper.fetch.legiscan import USER_AGENT

MIN_SECONDS_BETWEEN_REQUESTS = 1.0


class RobotsDisallowedError(Exception):
    pass


def _robots_url(url: str) -> str:
    parsed = urlparse(url)
    return urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")


def _is_allowed(client: httpx.Client, url: str) -> bool:
    robots_url = _robots_url(url)
    response = client.get(robots_url, headers={"User-Agent": USER_AGENT})
    parser = urllib.robotparser.RobotFileParser()
    if response.status_code >= 400:
        parser.allow_all = True
    else:
        parser.parse(response.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


def fetch_html(client: httpx.Client, url: str) -> tuple[str, int]:
    if not _is_allowed(client, url):
        raise RobotsDisallowedError(f"robots.txt disallows fetching {url}")

    response = client.get(url, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    time.sleep(MIN_SECONDS_BETWEEN_REQUESTS)
    return response.text, response.status_code
