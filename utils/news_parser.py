import asyncio, json, re
from pathlib import Path
from typing import Optional, Dict, Tuple
from aiohttp import ClientSession

NOTICE_URL = "https://feed.bithumb.com/notice/{}"
STATE_FILE = Path("storage/news_state.json")

TOKEN_PATTERNS = [
    re.compile(r"\(([A-Z0-9]{2,10})\)\s*원화\s*마켓"),
    re.compile(r"\(([A-Z0-9]{2,10})\)\s*마켓"),
    re.compile(r"\b([A-Z0-9]{2,10})\b\s*listing", re.I),
]

def _extract_token(text: str) -> Optional[str]:
    if not text:
        return None
    for rx in TOKEN_PATTERNS:
        m = rx.search(text)
        if m:
            return m.group(1)
    return None

def _load_last_id(default: int = 1649000) -> int:
    try:
        return json.loads(STATE_FILE.read_text()).get("last_id", default)
    except Exception:
        return default

def _save_last_id(nid: int) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"last_id": nid}, ensure_ascii=False))

async def _fetch_notice(session: ClientSession, nid: int) -> Tuple[int, Optional[str]]:
    url = NOTICE_URL.format(nid)
    try:
        async with session.get(url, timeout=5) as r:
            if r.status != 200:
                return nid, None
            html = await r.text()
    except Exception:
        return nid, None

    title = None
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        og = soup.find("meta", {"property": "og:title"})
        if og and og.get("content"):
            title = og["content"]
        if not title:
            h = soup.find(["h1", "h2"])
            if h:
                title = h.get_text(strip=True)
    except Exception:
        pass

    return nid, _extract_token(title or html)

async def find_latest_token(max_ahead: int = 80, concurrency: int = 10) -> Dict:
    last_id = _load_last_id()
    ids = list(range(last_id + 1, last_id + max_ahead + 1))

    async with ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        sem = asyncio.Semaphore(concurrency)

        async def one(n):
            async with sem:
                return await _fetch_notice(session, n)

        tasks = [asyncio.create_task(one(n)) for n in ids]
        for fut in asyncio.as_completed(tasks):
            nid, token = await fut
            if token:
                _save_last_id(nid)
                return {"ok": True, "notice_id": nid, "token": token}

    return {"ok": False, "error": "no token in window", "checked_window": [ids[0], ids[-1]]}