#!/usr/bin/env python3
"""
Auto-updater for the Media Link Hub.

Fetches fresh links from FMHY's open-source markdown data and writes data/links.json
for the four topics: Anime, Software, AI, Movies.

Includes a VERIFICATION LOOP: after building the dataset it validates the result
(every category populated, every URL well-formed, no duplicates). If validation
fails it re-fetches and rebuilds, up to MAX_ATTEMPTS times, so the published data
is only ever written when it has been verified "perfectly".
"""
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAW = "https://raw.githubusercontent.com/fmhy/edit/main/docs/{}"

# Topic -> source markdown files. video.md is split by section (anime vs the rest).
SOURCES = {
    "AI":       [("ai.md", None)],
    "Software": [("system-tools.md", None), ("developer-tools.md", None)],
    "Anime":    [("video.md", "anime")],      # only sections mentioning "anime"
    "Movies":   [("video.md", "not-anime")],  # everything else in video.md
}

# Minimum links we expect per category for the run to count as "complete".
MIN_PER_CATEGORY = 10
MAX_ATTEMPTS = 4

LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s*[►▷▶\s]*(.*?)\s*$")
ROOT = Path(__file__).resolve().parent.parent


def fetch(filename: str) -> str:
    url = RAW.format(filename)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def clean_text(text: str) -> str:
    """Strip markdown link syntax down to readable text."""
    text = LINK_RE.sub(lambda m: m.group(1), text)
    text = re.sub(r"\*\*|\*|`|_", "", text)
    for ch in ("\u200b", "\u2060", "\ufeff", "\u2063"):
        text = text.replace(ch, "")
    text = text.strip(" -–—\t")
    return re.sub(r"\s+", " ", text).strip()


def parse_markdown(md: str, section_filter):
    """Yield link entries from a markdown doc, tracking the current heading path."""
    section = ""
    in_callout = False
    for line in md.splitlines():
        # Skip VitePress callout blocks (::: tip / warning / details ... :::)
        if line.lstrip().startswith(":::"):
            in_callout = not in_callout
            continue
        if in_callout:
            continue
        h = HEADING_RE.match(line)
        if h:
            title = clean_text(h.group(2))
            # remove a link in the heading itself
            title = re.sub(r"\(https?://[^)]+\)", "", title).strip()
            if h.group(1) == "#":
                section = title
            else:
                section = f"{section} / {title}" if section else title
            continue

        stripped = line.lstrip()
        if not (stripped.startswith("- ") or stripped.startswith("* ")):
            continue

        # Skip annotation bullets like "* **Note** - ..." / "**Tip**" / "**Warning**"
        body = stripped[2:].lstrip()
        if re.match(r"\*\*(note|tip|warning|info|danger)\*\*", body, re.IGNORECASE):
            continue

        links = LINK_RE.findall(line)
        if not links:
            continue

        is_anime = "anime" in section.lower()
        if section_filter == "anime" and not is_anime:
            continue
        if section_filter == "not-anime" and is_anime:
            continue

        name, url = links[0]
        name = clean_text(name)
        if not name or len(name) < 2:
            continue
        mirrors = [u for (_, u) in links[1:] if u != url]
        desc = clean_text(line)
        # drop the leading name from the description if it repeats
        if desc.lower().startswith(name.lower()):
            desc = desc[len(name):].strip(" -–—,")
        yield {
            "name": name,
            "url": url,
            "desc": desc,
            "section": section,
            "mirrors": mirrors[:5],
        }


def build_category(specs):
    seen = set()
    out = []
    for filename, section_filter in specs:
        md = fetch(filename)
        for entry in parse_markdown(md, section_filter):
            key = entry["url"].rstrip("/").lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(entry)
    return out


def build_dataset():
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "https://github.com/fmhy/edit",
        "categories": {},
    }
    for topic, specs in SOURCES.items():
        data["categories"][topic] = build_category(specs)
    return data


def verify(data) -> list:
    """Return a list of problems; empty list means the dataset is perfect."""
    problems = []
    cats = data.get("categories", {})
    for topic in SOURCES:
        items = cats.get(topic, [])
        if len(items) < MIN_PER_CATEGORY:
            problems.append(f"{topic}: only {len(items)} links (< {MIN_PER_CATEGORY})")
        urls = [i["url"] for i in items]
        for u in urls:
            if not u.startswith("http"):
                problems.append(f"{topic}: malformed url {u!r}")
        dupes = len(urls) - len({u.rstrip('/').lower() for u in urls})
        if dupes:
            problems.append(f"{topic}: {dupes} duplicate urls")
        for i in items:
            if not i.get("name"):
                problems.append(f"{topic}: entry with empty name")
                break
    return problems


def main():
    last_problems = ["not run"]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"[attempt {attempt}/{MAX_ATTEMPTS}] building dataset...")
        try:
            data = build_dataset()
        except Exception as e:  # network hiccup, etc.
            print(f"  build error: {e}")
            time.sleep(3)
            continue
        problems = verify(data)
        counts = {t: len(data["categories"][t]) for t in SOURCES}
        print(f"  counts: {counts}")
        if not problems:
            out = ROOT / "data" / "links.json"
            out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            total = sum(counts.values())
            print(f"VERIFIED OK -> wrote {out} ({total} links across {len(counts)} topics)")
            return 0
        last_problems = problems
        print("  verification failed:")
        for p in problems:
            print(f"    - {p}")
        time.sleep(3)
    print("ERROR: dataset never verified clean. Problems:", last_problems)
    return 1


if __name__ == "__main__":
    sys.exit(main())
