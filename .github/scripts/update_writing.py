"""Fetch the latest Substack posts and write them into index.html.

Replaces everything between the <!-- writing:start --> and <!-- writing:end -->
markers. Leaves the file untouched if the feed can't be read or is empty.
"""
import html
import pathlib
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FEED = "https://sinanh.substack.com/feed"
LIMIT = 5
PAGE = pathlib.Path(__file__).resolve().parents[2] / "index.html"
START, END = "<!-- writing:start -->", "<!-- writing:end -->"
INDENT = "      "


def fetch_posts():
    req = urllib.request.Request(FEED, headers={"User-Agent": "sinanh.github.io feed updater"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        root = ET.fromstring(resp.read())
    posts = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        date = item.findtext("pubDate")
        if not (title and link and date):
            continue
        posts.append((parsedate_to_datetime(date), title, link))
    posts.sort(reverse=True)
    return posts[:LIMIT]


def render(posts):
    rows = []
    for when, title, link in posts:
        rows.append(
            f'{INDENT}<li><a href="{html.escape(link)}" target="_blank" rel="noopener">'
            f'<time datetime="{when:%Y-%m-%d}">{when:%Y-%m-%d}</time>'
            f'<span class="title">{html.escape(title, quote=False)}</span>'
            f'<span class="arrow">→</span></a></li>'
        )
    return "\n".join(rows)


def main():
    try:
        posts = fetch_posts()
    except Exception as exc:  # network or parse failure: keep the current list
        print(f"Could not read feed: {exc}", file=sys.stderr)
        return 1
    if not posts:
        print("Feed has no posts; leaving page unchanged.", file=sys.stderr)
        return 1

    page = PAGE.read_text(encoding="utf-8")
    try:
        head, rest = page.split(START, 1)
        _, tail = rest.split(END, 1)
    except ValueError:
        print("writing markers not found in index.html", file=sys.stderr)
        return 1

    new = f"{head}{START}\n{render(posts)}\n{INDENT}{END}{tail}"
    if new != page:
        PAGE.write_text(new, encoding="utf-8")
        print(f"Updated with {len(posts)} posts.")
    else:
        print("No new posts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
