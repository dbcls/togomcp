#!/usr/bin/env python3
"""Generate the "What's New" list on the intro page from CHANGELOG.md markers.

The `#whats-new` section of the public landing page
(`togo_mcp/data/docs/togomcp-intro.html`) is a curated, USER-FACING highlight
reel. To keep it in step with releases without a second hand-maintained log, the
curation lives as one-line markers in `CHANGELOG.md` and this script renders them
onto the page — so "update the CHANGELOG" also updates the intro page.

Marker syntax (an HTML comment, invisible in rendered Markdown — put one under
the release heading it describes, or under `[Unreleased]` for non-release news):

    <!-- whatsnew: 2026-07-24 | The MIE files were rewritten to a leaner format … -->

- Date is `YYYY-MM` or `YYYY-MM-DD` (shown verbatim, used for newest-first order).
- The text after `|` is trusted inline HTML (author-written, in-repo) — it may
  contain `<code>`, `<em>`, `<a …>`. Keep it to ONE user-facing sentence; do not
  include a literal `-->`.
- Only the newest MAX_ITEMS markers are rendered.

The rendered block is written between the `<!-- WHATSNEW:START -->` and
`<!-- WHATSNEW:END -->` sentinels inside `<ul class="whatsnew-list">`; nothing
else on the hand-edited page is touched (the intro page is edited in place, never
regenerated whole — see the intro-page-updater skill).

Usage:
    python scripts/generate_whatsnew.py            # rewrite the block in the HTML
    python scripts/generate_whatsnew.py --check     # exit 1 if the page is stale
    python scripts/generate_whatsnew.py --stdout     # print the whole HTML, don't write
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
HTML = REPO_ROOT / "togo_mcp" / "data" / "docs" / "togomcp-intro.html"

MAX_ITEMS = 5
INDENT = "      "  # the <li>/sentinel indent inside <ul class="whatsnew-list">
START = "<!-- WHATSNEW:START -->"
END = "<!-- WHATSNEW:END -->"

# One marker per line: <!-- whatsnew: DATE | text -->  (text is non-greedy up to -->)
_MARKER_RE = re.compile(
    r"<!--\s*whatsnew:\s*(\d{4}-\d{2}(?:-\d{2})?)\s*\|\s*(.*?)\s*-->"
)
_BLOCK_RE = re.compile(rf"[ \t]*{re.escape(START)}.*?{re.escape(END)}", re.S)


def load_markers():
    """Parse whatsnew markers from CHANGELOG.md, newest first, capped at MAX_ITEMS."""
    text = CHANGELOG.read_text(encoding="utf-8")
    markers = [
        {"date": m.group(1), "key": _sort_key(m.group(1)), "text": m.group(2).strip()}
        for m in _MARKER_RE.finditer(text)
    ]
    # Newest first; stable, so ties keep CHANGELOG order (newest release is on top).
    markers.sort(key=lambda x: x["key"], reverse=True)
    return markers[:MAX_ITEMS]


def _sort_key(date: str) -> str:
    return date if len(date) == 10 else f"{date}-01"  # pad YYYY-MM to a full date


def render_items(markers) -> str:
    if not markers:
        raise SystemExit(f"no `whatsnew:` markers found in {CHANGELOG.name} — refusing to empty the section")
    li = []
    for m in markers:
        li.append(
            f"{INDENT}<li>\n"
            f'{INDENT}  <span class="whatsnew-date">{m["date"]}</span>\n'
            f'{INDENT}  <span>{m["text"]}</span>\n'
            f"{INDENT}</li>"
        )
    return "\n".join(li)


def build() -> str:
    """Return the full intro-page HTML with the What's New block regenerated."""
    html = HTML.read_text(encoding="utf-8")
    block = f"{INDENT}{START}\n{render_items(load_markers())}\n{INDENT}{END}"
    new_html, n = _BLOCK_RE.subn(lambda _m: block, html)
    if n != 1:
        raise SystemExit(
            f"expected exactly one {START} … {END} region in {HTML.name}, found {n}"
        )
    return new_html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if the page is stale")
    ap.add_argument("--stdout", action="store_true", help="print the rebuilt HTML, do not write")
    args = ap.parse_args(argv)

    content = build()

    if args.stdout:
        sys.stdout.write(content)
        return 0

    if args.check:
        current = HTML.read_text(encoding="utf-8") if HTML.exists() else ""
        if current != content:
            print(
                f"What's New OUT OF SYNC: {HTML.relative_to(REPO_ROOT)} differs from the "
                "CHANGELOG whatsnew markers. Run: python scripts/generate_whatsnew.py",
                file=sys.stderr,
            )
            return 1
        print("What's New in sync.")
        return 0

    HTML.write_text(content, encoding="utf-8")
    print(f"wrote {HTML.relative_to(REPO_ROOT)} ({len(load_markers())} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
