import httpx
import pytest

from juniper.fetch.pdf_fetcher import fetch_pdf
from juniper.fetch.robots import RobotsDisallowedError

PDF_BYTES = b"%PDF-1.7 fake pdf content"


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_pdf_returns_bytes_when_allowed(monkeypatch):
    monkeypatch.setattr("juniper.fetch.pdf_fetcher.time.sleep", lambda _: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=PDF_BYTES)

    with _client(handler) as client:
        content, status = fetch_pdf(client, "https://example.com/report.pdf")

    assert content == PDF_BYTES
    assert status == 200


def test_fetch_pdf_raises_when_disallowed(monkeypatch):
    monkeypatch.setattr("juniper.fetch.pdf_fetcher.time.sleep", lambda _: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        return httpx.Response(200, content=PDF_BYTES)

    with _client(handler) as client, pytest.raises(RobotsDisallowedError):
        fetch_pdf(client, "https://example.com/report.pdf")


def test_fetch_pdf_missing_robots_defaults_to_allowed(monkeypatch):
    monkeypatch.setattr("juniper.fetch.pdf_fetcher.time.sleep", lambda _: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, content=PDF_BYTES)

    with _client(handler) as client:
        content, status = fetch_pdf(client, "https://example.com/report.pdf")

    assert content == PDF_BYTES
    assert status == 200


def test_fetch_pdf_respects_rate_limit(monkeypatch):
    sleep_calls = []
    monkeypatch.setattr("juniper.fetch.pdf_fetcher.time.sleep", sleep_calls.append)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=PDF_BYTES)

    with _client(handler) as client:
        fetch_pdf(client, "https://example.com/report.pdf")

    assert sleep_calls == [1.0]
