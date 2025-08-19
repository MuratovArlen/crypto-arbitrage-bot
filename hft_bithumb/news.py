import re
from typing import Optional, Dict, Any
from aiohttp import ClientSession
from bs4 import BeautifulSoup # type: ignore

TICKER_RE = re.compile(r"\b([A-Z]{2,10})\b")

async def fetch_html(session: ClientSession, url: str) -> str:
    async with session.get(url, timeout=5) as r:
        r.raise_for_status()
        return await r.text()

def extract_ticker(text: str) -> Optional[str]:
    # Простая эвристика: ищем токен из капслока, фильтруем шум
    for m in TICKER_RE.finditer(text):
        sym = m.group(1)
        if len(sym) < 2 or len(sym) > 10:
            continue
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
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.text.strip() if soup.title else ""
    # на реальном источнике можно искать по селекторам
    text = title or soup.get_text(separator=" ", strip=True)[:500]
    ticker = extract_ticker(text)
    if not ticker:
        return None
    return {
        "title": title,
        "text": text,
        "ticker": ticker,
        "sentiment": quick_sentiment(text),
    }

async def fetch_and_parse(session: ClientSession, url: str) -> Optional[Dict[str, Any]]:
    html = await fetch_html(session, url)
    return parse_news_html(html)
