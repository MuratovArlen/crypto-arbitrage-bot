from typing import Any, Optional, Dict
import re

try:
    from aiohttp import ClientSession  # type: ignore
except Exception:
    ClientSession = None  # type: ignore

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None  # type: ignore

TICKER_RE = re.compile(r"\b([A-Z]{2,10})\b")

async def fetch_html(session: Any, url: str) -> str:
    if ClientSession is None:
        raise ImportError("aiohttp is required to fetch HTML but is not installed")
    async with session.get(url, timeout=5) as r:
        r.raise_for_status()
        return await r.text()

def extract_ticker(text: str) -> Optional[str]:
    for m in TICKER_RE.finditer(text):
        sym = m.group(1)
        if 2 <= len(sym) <= 10:
            return sym
    return None

def quick_sentiment(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["listing", "lists", "listed", "partnership", "launch"]):
        return "positive"
    if any(w in t for w in ["delist", "hack", "suspend"]):
        return "negative"
    return "neutral"

def parse_news_html(html: str) -> Optional[Dict[str, Any]]:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.text.strip() if soup.title else ""
        text = title or soup.get_text(separator=" ", strip=True)[:500]
    else:
        title = ""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()[:500]

    ticker = extract_ticker(text)
    if not ticker:
        return None

    return {
        "title": title,
        "text": text,
        "ticker": ticker,
        "sentiment": quick_sentiment(text),
    }

async def fetch_and_parse(session: Any, url: str) -> Optional[Dict[str, Any]]:
    html = await fetch_html(session, url)
    return parse_news_html(html)
