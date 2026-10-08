"""Landing-page routes, and the TOGOMCP_TRIAL_CHAT switch that takes the chat off them."""
from pathlib import Path

import pytest
from starlette.testclient import TestClient

DOCS = Path(__file__).resolve().parents[1] / "togo_mcp" / "data" / "docs"
PAGES = {"/": "togomcp-intro.html", "/ja": "togomcp-intro-ja.html"}
START, END = "<!-- TRIAL-CHAT:START -->", "<!-- TRIAL-CHAT:END -->"


@pytest.fixture
def client(monkeypatch):
    from togo_mcp.main import mcp

    monkeypatch.delenv("TOGOMCP_TRIAL_CHAT", raising=False)
    with TestClient(mcp.http_app()) as c:
        yield c


@pytest.mark.parametrize("name", PAGES.values())
def test_page_marks_every_chat_region(name):
    """The switch removes what lies between the sentinels, so a pair lost in a hand
    edit would leave half the chat on the page (or swallow the content after it)."""
    html = (DOCS / name).read_text(encoding="utf-8")
    assert html.count(START) == html.count(END) == 3
    regions = [r.split(END)[0] for r in html.split(START)[1:]]
    assert "#llm-meta-widget-toggle" in regions[0]            # launcher position, in <head>
    assert 'id="open-trial-chat"' in regions[1]
    assert "<llm-meta-widget " in regions[2] and "#open-trial-chat" in regions[2]
    outside = html.split(START)[0] + "".join(r.split(END)[1] for r in html.split(START)[1:])
    assert "llm-meta-widget" not in outside and "open-trial-chat" not in outside


@pytest.mark.parametrize("route", PAGES)
def test_chat_is_on_by_default(client, route):
    r = client.get(route)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "<llm-meta-widget " in r.text and 'id="open-trial-chat"' in r.text


@pytest.mark.parametrize("value", ["0", "false", "No", " off "])
@pytest.mark.parametrize("route", PAGES)
def test_switch_removes_the_chat_and_nothing_else(client, monkeypatch, route, value):
    on = client.get(route).text
    monkeypatch.setenv("TOGOMCP_TRIAL_CHAT", value)
    off = client.get(route).text
    assert "llm-meta-widget" not in off and "open-trial-chat" not in off
    assert "TRIAL-CHAT" not in off
    # the rest of the page survives: language links, What's New, the closing tags
    assert '<a href="/ja">' in off and 'id="whats-new"' in off
    assert off.rstrip().endswith("</html>")
    regions = (DOCS / PAGES[route]).read_text(encoding="utf-8").count(START)
    assert len(on.splitlines()) - len(off.splitlines()) > regions


@pytest.mark.parametrize("value", ["", "1", "true", "anything"])
def test_only_an_explicit_off_disables(client, monkeypatch, value):
    monkeypatch.setenv("TOGOMCP_TRIAL_CHAT", value)
    assert "<llm-meta-widget " in client.get("/").text


def test_japanese_note_outlives_the_chat(client, monkeypatch):
    monkeypatch.setenv("TOGOMCP_TRIAL_CHAT", "0")
    assert "以下の技術説明は英語です。" in client.get("/ja").text


def test_widget_asset_is_served_as_javascript(client):
    r = client.get("/assets/llm-meta-widget.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/javascript")
    assert len(r.content) == (DOCS / "assets" / "llm-meta-widget.js").stat().st_size
