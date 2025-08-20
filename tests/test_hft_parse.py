from typing import Optional, Any
from bs4 import BeautifulSoup  # type: ignore
import re


TICKER_RE = re.compile(r"\b([A-Z]{2,10})\b")

async def fetch_html(session: Any, url: str) -> str:
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

def parse_news_html(html: str):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.text.strip() if soup.title else ""
    text = title or soup.get_text(separator=" ", strip=True)[:500]
    ticker = extract_ticker(text)
    if not ticker:
        return None
    return {"title": title, "text": text, "ticker": ticker, "sentiment": quick_sentiment(text)}
