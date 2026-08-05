import urllib.robotparser
from urllib.parse import urljoin, urlparse

import httpx

from juniper.fetch.legiscan import USER_AGENT


class RobotsDisallowedError(Exception):
    pass


def _robots_url(url: str) -> str:
    parsed = urlparse(url)
    return urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")


def is_allowed(client: httpx.Client, url: str) -> bool:
    robots_url = _robots_url(url)
    response = client.get(robots_url, headers={"User-Agent": USER_AGENT})
    parser = urllib.robotparser.RobotFileParser()
    if response.status_code >= 400:
        parser.allow_all = True
    else:
        parser.parse(response.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)
