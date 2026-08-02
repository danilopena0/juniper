import hashlib
import re

from selectolax.parser import HTMLParser

STRIPPED_TAGS = ["script", "style", "nav", "header", "footer", "noscript"]

TIMESTAMP_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2},?\s+\d{4}\b"
    ),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    re.compile(r"\b\d{1,2}:\d{2}\s*(AM|PM|am|pm)\b"),
    re.compile(r"©\s*\d{4}"),
]

TIMESTAMP_PLACEHOLDER = "[DATE]"


def normalize_html(html: str) -> str:
    tree = HTMLParser(html)
    for tag in STRIPPED_TAGS:
        for node in tree.css(tag):
            node.decompose()

    text = tree.body.text(separator=" ") if tree.body else tree.text(separator=" ")
    text = " ".join(text.split())

    for pattern in TIMESTAMP_PATTERNS:
        text = pattern.sub(TIMESTAMP_PLACEHOLDER, text)

    return " ".join(text.split())


def hash_normalized(normalized: str) -> str:
    return hashlib.sha256(normalized.encode()).hexdigest()
