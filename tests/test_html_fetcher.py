import httpx
import pytest

from juniper.fetch.html_fetcher import RobotsDisallowedError, fetch_html


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_html_returns_body_when_allowed(monkeypatch):
    monkeypatch.setattr("juniper.fetch.html_fetcher.time.sleep", lambda _: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text="<html>ok</html>")

    with _client(handler) as client:
        html, status = fetch_html(client, "https://example.com/dockets")

    assert html == "<html>ok</html>"
    assert status == 200


def test_fetch_html_raises_when_disallowed(monkeypatch):
    monkeypatch.setattr("juniper.fetch.html_fetcher.time.sleep", lambda _: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        return httpx.Response(200, text="<html>should not reach here</html>")

    with _client(handler) as client, pytest.raises(RobotsDisallowedError):
        fetch_html(client, "https://example.com/dockets")


def test_fetch_html_missing_robots_defaults_to_allowed(monkeypatch):
    monkeypatch.setattr("juniper.fetch.html_fetcher.time.sleep", lambda _: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text="<html>ok</html>")

    with _client(handler) as client:
        html, status = fetch_html(client, "https://example.com/dockets")

    assert html == "<html>ok</html>"
    assert status == 200


def test_fetch_html_respects_rate_limit(monkeypatch):
    sleep_calls = []
    monkeypatch.setattr("juniper.fetch.html_fetcher.time.sleep", sleep_calls.append)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text="<html>ok</html>")

    with _client(handler) as client:
        fetch_html(client, "https://example.com/dockets")

    assert sleep_calls == [1.0]
