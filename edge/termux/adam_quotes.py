#!/usr/bin/env python3
"""Deterministic, offline, source-carrying quotations for Adam."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import os
import pathlib
from typing import Iterable


@dataclass(frozen=True)
class Quote:
    identifier: str
    category: str
    text: str
    attribution: str
    work: str
    source_url: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


QUOTES: tuple[Quote, ...] = (
    Quote(
        "galatians-6-9",
        "bible",
        "And let us not be weary in well doing: for in due season we shall reap, if we faint not.",
        "King James Version",
        "Galatians 6:9",
        "https://www.gutenberg.org/cache/epub/8048/pg8048-images.html",
    ),
    Quote(
        "galatians-5-1",
        "bible",
        "Stand fast therefore in the liberty wherewith Christ hath made us free, and be not entangled again with the yoke of bondage.",
        "King James Version",
        "Galatians 5:1",
        "https://www.gutenberg.org/cache/epub/8048/pg8048-images.html",
    ),
    Quote(
        "ecclesiastes-9-10",
        "bible",
        "Whatsoever thy hand findeth to do, do it with thy might.",
        "King James Version",
        "Ecclesiastes 9:10",
        "https://www.gutenberg.org/cache/epub/8021/pg8021-images.html",
    ),
    Quote(
        "proverbs-24-16",
        "bible",
        "For a just man falleth seven times, and riseth up again.",
        "King James Version",
        "Proverbs 24:16",
        "https://www.gutenberg.org/cache/epub/8020/pg8020-images.html",
    ),
    Quote(
        "hamlet-readiness",
        "literature",
        "The readiness is all.",
        "William Shakespeare",
        "Hamlet, Act 5, scene 2",
        "https://www.folger.edu/podcasts/shakespeare-unlimited/shakespeare-solace/",
    ),
    Quote(
        "coriolanus-action",
        "literature",
        "Action is eloquence.",
        "William Shakespeare",
        "Coriolanus, Act 3, scene 2",
        "https://www.folger.edu/explore/shakespeares-works/coriolanus/read/3/2/",
    ),
    Quote(
        "ulysses-strive",
        "literature",
        "To strive, to seek, to find, and not to yield.",
        "Alfred, Lord Tennyson",
        "Ulysses",
        "https://www.gutenberg.org/files/8601/8601-h/8601-h.htm",
    ),
    Quote(
        "douglass-struggle",
        "history",
        "If there is no struggle, there is no progress.",
        "Frederick Douglass",
        "West India Emancipation speech",
        "https://www.loc.gov/pictures/item/2023632628/",
    ),
    Quote(
        "lincoln-task",
        "history",
        "It is for us the living rather to be dedicated here to the great task remaining before us.",
        "Abraham Lincoln",
        "Gettysburg Address",
        "https://www.archives.gov/files/legislative/resources/education/reviewing-civil-war-reconstruction/primary-source-sheets.pdf",
    ),
    Quote(
        "kennedy-hard",
        "history",
        "We choose to go to the Moon in this decade and do the other things, not because they are easy, but because they are hard.",
        "John F. Kennedy",
        "Address at Rice University, September 12, 1962",
        "https://www.jfklibrary.org/learn/about-jfk/historic-speeches/address-at-rice-university-on-the-nations-space-effort",
    ),
)

CATEGORIES = frozenset(quote.category for quote in QUOTES)


def context_seed(cwd: pathlib.Path | None = None) -> str:
    explicit = os.environ.get("ADAM_QUOTE_SEED")
    if explicit:
        return explicit
    parts = (
        os.environ.get("ADAM_QUOTE_DAY", date.today().isoformat()),
        os.environ.get("ADAM_ANVIL", "unmarked-anvil"),
        os.environ.get("ADAM_TEAM", "unmarked-team"),
        str((cwd or pathlib.Path.cwd()).resolve()),
    )
    return "|".join(parts)


def select_quote(seed: str, category: str | None = None) -> Quote:
    if not seed:
        raise ValueError("quote seed must not be empty")
    if category is not None and category not in CATEGORIES:
        raise ValueError(f"unknown quote category: {category}")
    candidates: Iterable[Quote] = QUOTES
    if category is not None:
        candidates = (quote for quote in QUOTES if quote.category == category)
    ordered = tuple(candidates)
    digest = hashlib.sha256(
        f"continue-continue.adam-quote.v1\0{category or '*'}\0{seed}".encode("utf-8")
    ).digest()
    return ordered[int.from_bytes(digest[:8], "big") % len(ordered)]


def format_quote(quote: Quote) -> str:
    return (
        f"[quote:{quote.category}:{quote.identifier}] “{quote.text}” "
        f"— {quote.attribution}, {quote.work}"
    )
