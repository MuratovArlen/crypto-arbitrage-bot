import pytest

from hft_bithumb.news import extract_ticker, quick_sentiment, parse_news_html


def test_extract_ticker_from_korean_title():
    # ТЗ: строка вида "스파크(SPK) 원화 마켓 추가 …"
    html = "<html><head><title>스파크(SPK) 원화 마켓 추가 (거래 오픈 오후 07:30 예정)</title></head><body></body></html>"
    parsed = parse_news_html(html)
    assert parsed is not None
    assert parsed["ticker"] == "SPK"


def test_parse_returns_none_when_no_ticker():
    html = "<html><head><title>Planned maintenance window announced</title></head></html>"
    assert parse_news_html(html) is None


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Bithumb lists NEW token on KRW market", "positive"),
        ("Emergency notice: market suspended due to hack", "negative"),
        ("General update without strong words", "neutral"),
    ],
)
def test_quick_sentiment(text, expected):
    assert quick_sentiment(text) == expected


def test_extract_ticker_simple_english():
    text = "New listing: ABC will launch today"
    assert extract_ticker(text) == "ABC"
