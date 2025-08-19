from typing import Optional, Dict, Any, List

def decide_on_news(news: Dict[str, Any], whitelist: List[str]) -> Optional[Dict[str, Any]]:
    """
    Возвращает сигнал {"ticker": "BTC", "strength": float}
    если новость позитивная и тикер в белом списке.
    """
    if not news:
        return None
    ticker = news["ticker"].upper()
    if whitelist and ticker not in [t.upper() for t in whitelist]:
        return None
    if news.get("sentiment") == "positive":
        return {"ticker": ticker, "strength": 1.0}
    return None
