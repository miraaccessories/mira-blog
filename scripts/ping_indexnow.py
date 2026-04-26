#!/usr/bin/env python3
"""IndexNow ping — notifies Bing/Yandex/Seznam of new or changed URLs.

Run AFTER `git push` to main (which deploys to GitHub Pages). The ping tells
search engines to re-crawl immediately instead of waiting for their schedule.

  python3 scripts/ping_indexnow.py            # ping all URLs from sitemap.xml
  python3 scripts/ping_indexnow.py <url> ...  # ping specific URLs only

Stdlib only. Free protocol — no API quota.
Key file must be live at: https://blog.miraaccessories.co.za/<KEY>.txt
"""
from __future__ import annotations
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOST = "blog.miraaccessories.co.za"
KEY = "8912847107344fa29b7b5adb6c54e6ce"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"


def urls_from_sitemap() -> list[str]:
    sitemap = ROOT / "dist" / "sitemap.xml"
    if not sitemap.exists():
        print(f"  ✗ {sitemap} missing — run `python3 scripts/build.py` first")
        sys.exit(1)
    return re.findall(r"<loc>([^<]+)</loc>", sitemap.read_text(encoding="utf-8"))


def ping(urls: list[str]) -> None:
    if not urls:
        print("  no URLs to ping"); return
    payload = {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"  ✓ IndexNow accepted {len(urls)} URL(s) — HTTP {r.status}")
    except urllib.error.HTTPError as e:
        # 200/202 = success; 400 = bad request; 422 = URLs don't match host
        msg = e.read()[:200].decode("utf-8", "replace")
        if e.code in (200, 202):
            print(f"  ✓ IndexNow accepted {len(urls)} URL(s) — HTTP {e.code}")
        else:
            print(f"  ✗ IndexNow returned {e.code}: {msg}"); sys.exit(1)
    except Exception as e:
        print(f"  ✗ IndexNow ping failed: {e}"); sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    urls = args if args else urls_from_sitemap()
    print(f"  pinging IndexNow for {len(urls)} URL(s) (key file: {KEY_LOCATION})")
    ping(urls)
