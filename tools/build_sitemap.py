#!/usr/bin/env python3
"""Build sitemap.xml from the HTML pages in the repository.

Lists every published .html page that is not noindex, by its canonical URL, with <lastmod>
taken from the last git commit that changed the file (W3C datetime, with time zone).

  python3 tools/build_sitemap.py           # rewrite sitemap.xml
  python3 tools/build_sitemap.py --check   # exit 1 if sitemap.xml lists a different set of URLs
Run it after committing page changes, then commit sitemap.xml.
"""
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

SITE = "https://kayjoyflowers.online"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"reports", "docs", "tools", "node_modules"}
ORDER = ["/", "/fearlessly-unfuckwithable.html", "/genius-insight.html", "/library.html", "/about.html", "/privacy.html"]


def pages():
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith((".", "_"))]
        for f in files:
            # 404 page and search-engine verification files (e.g. google1234abcd.html) are never listed
            if not f.endswith(".html") or f == "404.html" or re.fullmatch(r"google[0-9a-f]+\.html", f):
                continue
            full = os.path.join(dirpath, f)
            html = open(full, encoding="utf-8").read()
            if re.search(r'<meta\s+name="robots"\s+content="[^"]*noindex', html, re.I):
                continue
            rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
            url = "/" + rel
            if url.endswith("/index.html"):
                url = url[: -len("index.html")]
            yield url, rel


def lastmod(rel):
    dirty = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not dirty:
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", rel], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if out:
            return out
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main():
    found = sorted(pages(), key=lambda p: (ORDER.index(p[0]) if p[0] in ORDER else 99, p[0]))
    path = os.path.join(ROOT, "sitemap.xml")
    if "--check" in sys.argv:
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        listed = {e.text.strip() for e in ET.parse(path).getroot().findall(".//s:loc", ns)}
        want = {SITE + u for u, _ in found}
        if listed != want:
            print("sitemap.xml is out of date.")
            for u in sorted(want - listed):
                print("  missing:", u)
            for u in sorted(listed - want):
                print("  should not be listed:", u)
            print("Run: python3 tools/build_sitemap.py")
            sys.exit(1)
        print(f"sitemap.xml OK ({len(want)} URLs)")
        return
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, rel in found:
        lines.append(f"  <url><loc>{SITE}{url}</loc><lastmod>{lastmod(rel)}</lastmod></url>")
    lines.append("</urlset>")
    open(path, "w").write("\n".join(lines) + "\n")
    print(f"Wrote sitemap.xml ({len(found)} URLs)")


if __name__ == "__main__":
    main()
