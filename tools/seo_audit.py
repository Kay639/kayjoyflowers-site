#!/usr/bin/env python3
"""Kay Joy Flowers SEO / AEO audit.

A repeatable, dependency-free audit (Python 3.9+ standard library only).

It crawls the site the way a search engine would: it starts at the home page,
reads robots.txt and sitemap.xml, follows every internal link, and also checks
the private pages that must stay out of search. Every check has a fixed
category, severity and weight, so the same site always gets the same score.
See docs/seo-aeo/audit-methodology.md for the rules.

Usage
  Live site:   python3 tools/seo_audit.py --base https://kayjoyflowers.online
  Local copy:  python3 tools/seo_audit.py --root .        (serves the folder like GitHub Pages)
  Options:     --json out.json   write the full result
               --offline         skip checks that need the internet (checkout links, OG images)
               --fail-on high    exit 1 if any check of this severity or worse fails (for CI)
"""
from __future__ import annotations

import argparse
import functools
import html
import http.server
import json
import os
import re
import socketserver
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

SITE = "https://kayjoyflowers.online"

# Pages that must never be indexed (payment-gated forms, sign-in, redirects).
PRIVATE_PATHS = ["/scan-intake.html", "/companion/", "/companion-sovereign/"]
# Folders the Jekyll build excludes (see _config.yml); never published.
UNPUBLISHED_DIRS = ("reports", "docs", "tools", ".github", "node_modules")

# AI search/answer crawlers that must stay allowed (they power citations).
# Training crawlers (GPTBot, ClaudeBot, Google-Extended) are blocked by choice and not checked here.
AI_CRAWLERS = ["OAI-SearchBot", "ChatGPT-User", "PerplexityBot", "Claude-SearchBot", "Bingbot"]
TRAINING_CRAWLERS = ["GPTBot", "ClaudeBot", "Google-Extended"]
CHECKOUT_HOSTS = ("shop.beacons.ai", "buy.stripe.com", "billing.stripe.com")

SEVERITY_WEIGHT = {"critical": 5, "high": 3, "medium": 2, "low": 1}
SEVERITY_ORDER = ["critical", "high", "medium", "low"]
CATEGORIES = ["Technical SEO", "Metadata & Social", "Structured Data",
              "AEO & Content", "Accessibility", "Performance", "Conversion"]

# id: (category, severity, title, principle, fix)
CHECKS = {
    # ---- Technical SEO
    "robots_present": ("Technical SEO", "high", "robots.txt is published",
        "Crawlers request /robots.txt first. Without it they assume everything is allowed but find no sitemap pointer.",
        "Publish robots.txt at the site root with a Sitemap: line."),
    "robots_allows_site": ("Technical SEO", "critical", "robots.txt does not block the site",
        "A stray 'Disallow: /' removes the whole site from search.",
        "Keep 'Allow: /' for User-agent: *."),
    "robots_sitemap": ("Technical SEO", "medium", "robots.txt points to the sitemap",
        "The Sitemap line is how crawlers without Search Console access find every page.",
        "Add 'Sitemap: https://kayjoyflowers.online/sitemap.xml'."),
    "sitemap_present": ("Technical SEO", "high", "sitemap.xml is published and valid",
        "A sitemap lists the canonical URLs you want indexed and when they last changed.",
        "Publish sitemap.xml listing every indexable page by its canonical URL."),
    "sitemap_complete": ("Technical SEO", "medium", "Indexable page is listed in the sitemap",
        "Pages missing from the sitemap are discovered later, or not at all if they are weakly linked.",
        "Add the page's canonical URL to sitemap.xml."),
    "sitemap_clean": ("Technical SEO", "high", "Sitemap URL is live, indexable and canonical",
        "Listing redirects, 404s or noindex pages sends search engines mixed signals and wastes crawl budget.",
        "Only list 200-status, indexable, self-canonical URLs."),
    "status_ok": ("Technical SEO", "critical", "Page returns HTTP 200",
        "Only pages that load can be indexed or cited.",
        "Restore the page or remove links to it."),
    "not_found_status": ("Technical SEO", "medium", "Missing URLs return a real 404",
        "Soft 404s (200 status for missing pages) get indexed as thin duplicates.",
        "Let GitHub Pages return 404; provide a branded 404.html."),
    "canonical_present": ("Technical SEO", "high", "Canonical URL declared",
        "GitHub Pages serves the same page at /about, /about.html and with query strings. The canonical tag says which one counts.",
        "Add <link rel=\"canonical\" href=\"https://kayjoyflowers.online/...\">."),
    "canonical_self": ("Technical SEO", "high", "Canonical points to this page's own URL",
        "A canonical pointing elsewhere tells Google to drop this page in favour of another.",
        "Make the canonical the page's own absolute https URL."),
    "viewport": ("Technical SEO", "high", "Mobile viewport declared",
        "Google indexes the mobile version first.",
        "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">."),
    "internal_links_ok": ("Technical SEO", "high", "Internal links resolve",
        "Broken internal links waste crawl paths and lose visitors.",
        "Fix or remove the broken link."),
    "anchors_ok": ("Technical SEO", "low", "In-page anchors exist",
        "A link to #section that doesn't exist silently fails.",
        "Give the target element the matching id."),
    "not_orphan": ("Technical SEO", "medium", "Page is linked from another public page",
        "Pages no other page links to are hard for crawlers and people to find.",
        "Link to the page from the navigation, footer or a related page."),
    "private_noindex": ("Technical SEO", "high", "Private page is kept out of search",
        "Payment-gated forms and sign-in screens should never appear in search results.",
        "Add <meta name=\"robots\" content=\"noindex, nofollow\"> and keep it out of the sitemap."),
    # ---- Metadata & Social
    "title_present": ("Metadata & Social", "critical", "Page has a title",
        "The title is the blue link in search results and the default share text.",
        "Write a unique <title>."),
    "title_length": ("Metadata & Social", "low", "Title is 15-65 characters",
        "Longer titles are cut off in results; very short ones waste the most important text on the page.",
        "Lead with the page's subject, end with the brand."),
    "title_unique": ("Metadata & Social", "high", "Title is unique across the site",
        "Duplicate titles make pages compete with each other.",
        "Give each page its own title."),
    "desc_present": ("Metadata & Social", "high", "Meta description present",
        "Search engines and AI answers often quote it as the summary.",
        "Write a 70-160 character description of what the visitor gets."),
    "desc_length": ("Metadata & Social", "low", "Description is 70-160 characters",
        "Too short wastes the snippet; too long is truncated.",
        "Edit to 70-160 characters."),
    "desc_unique": ("Metadata & Social", "medium", "Description is unique",
        "Duplicate descriptions are often ignored and rewritten by Google.",
        "Write one description per page."),
    "og_complete": ("Metadata & Social", "medium", "Open Graph tags complete",
        "og:title, og:description, og:image, og:url and og:type control the preview in Facebook, Instagram DMs, iMessage, Slack and LinkedIn.",
        "Add the five og: tags."),
    "og_url_canonical": ("Metadata & Social", "low", "og:url matches the canonical",
        "Shares and search should consolidate on the same URL.",
        "Use the canonical URL for og:url."),
    "og_image_ok": ("Metadata & Social", "low", "og:image loads",
        "A broken share image produces a blank preview.",
        "Use an absolute, publicly reachable image URL."),
    "twitter_card": ("Metadata & Social", "low", "Twitter/X card declared",
        "Without it X shows a small text-only preview.",
        "Add <meta name=\"twitter:card\" content=\"summary_large_image\">."),
    # ---- Structured Data
    "jsonld_present": ("Structured Data", "medium", "JSON-LD structured data present",
        "Structured data states facts (who wrote this, what it costs) in a form machines don't have to guess at.",
        "Add a JSON-LD block describing the page's main entity."),
    "jsonld_valid": ("Structured Data", "high", "JSON-LD parses",
        "One syntax error makes the whole block invisible.",
        "Fix the JSON syntax."),
    "jsonld_required": ("Structured Data", "high", "Schema types have their required properties",
        "Incomplete types (an Offer without a price, a Book without an author) are ignored for rich results.",
        "Add the missing properties."),
    "jsonld_prices_visible": ("Structured Data", "high", "Structured-data prices match visible prices",
        "Google penalises markup that disagrees with what visitors see. Prices must match exactly.",
        "Use the exact price shown on the page."),
    "faq_visible": ("Structured Data", "high", "FAQ markup matches visible questions",
        "FAQPage markup must mirror questions and answers that are visible on the page.",
        "Only mark up questions that appear on the page, word for word."),
    "breadcrumbs": ("Structured Data", "low", "BreadcrumbList on inner pages",
        "Breadcrumbs show the page's place in the site in search results.",
        "Add a BreadcrumbList node."),
    "entity_home": ("Structured Data", "high", "Home page defines the WebSite and the author (Person)",
        "Answer engines resolve 'who is Kay Joy Flowers' from a single, consistent Person entity with sameAs links.",
        "Add WebSite and Person nodes with a stable @id."),
    "entity_consistent": ("Structured Data", "medium", "Person entity is consistent across pages",
        "Conflicting names or IDs split the entity in knowledge graphs.",
        "Reuse the same @id and name everywhere."),
    # ---- AEO & Content
    "h1_single": ("AEO & Content", "high", "Exactly one H1",
        "The H1 is the page's headline for machines. Zero or several blurs the topic.",
        "Use one H1 that states the page's subject."),
    "heading_order": ("AEO & Content", "low", "Headings don't skip levels",
        "Answer engines use the heading outline to split a page into quotable sections.",
        "Go H1 > H2 > H3 without skipping."),
    "word_count": ("AEO & Content", "medium", "At least 250 words of visible text",
        "Thin pages give search and answer engines little to understand or quote.",
        "Add genuinely useful text (descriptions, answers), never filler."),
    "author_attribution": ("AEO & Content", "medium", "Author is attributed",
        "Clear authorship is a core credibility signal for search and AI answers.",
        "Add <meta name=\"author\"> and author/Person in JSON-LD."),
    "llms_txt": ("AEO & Content", "low", "llms.txt published (optional discovery aid)",
        "llms.txt is a proposed convention, not a ranking factor. It is a cheap, plain-language map for AI tools.",
        "Publish /llms.txt with a short summary and key links."),
    "ai_crawlers_allowed": ("AEO & Content", "medium", "AI search crawlers are not blocked",
        "ChatGPT Search, Perplexity and Claude can only cite pages their search crawlers may read. Blocking training crawlers does not affect this.",
        "Keep OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot and Bingbot allowed in robots.txt."),
    # ---- Accessibility
    "lang": ("Accessibility", "medium", "<html lang> set",
        "Screen readers and translators need the page language.",
        "Use <html lang=\"en\">."),
    "img_alt": ("Accessibility", "high", "Images have descriptive alt text",
        "Alt text is read aloud to blind visitors and used by search engines to understand images.",
        "Describe the image (e.g. 'Fearlessly Unfuckwithable by Kay Joy Flowers, book cover')."),
    "link_text": ("Accessibility", "medium", "Links have discernible text",
        "Screen-reader users navigate by link text.",
        "Give every link visible text or an aria-label."),
    "skip_link": ("Accessibility", "low", "Skip-to-content link",
        "Keyboard users shouldn't have to tab through the menu on every page.",
        "Add a visually hidden 'Skip to content' link targeting <main id=\"main\">."),
    # ---- Performance
    "img_dimensions": ("Performance", "medium", "Images declare width and height",
        "Without dimensions the layout jumps as images load (Cumulative Layout Shift).",
        "Add width and height attributes matching the aspect ratio."),
    "lcp_not_lazy": ("Performance", "high", "Hero image is not lazy-loaded",
        "The largest above-the-fold image is usually the Largest Contentful Paint. Lazy-loading it delays LCP.",
        "Remove loading=\"lazy\" from the first image and add fetchpriority=\"high\"."),
    "html_weight": ("Performance", "low", "HTML under 100 KB",
        "Small HTML parses fast on mobile networks.",
        "Move repeated inline code into shared files."),
    # ---- Conversion
    "checkout_links_ok": ("Conversion", "critical", "Checkout links resolve",
        "A broken checkout link is a lost sale.",
        "Replace with the current Beacons or Stripe link."),
    "hero_cta": ("Conversion", "medium", "Clear call to action in the first screen",
        "Visitors decide in seconds. The first section should offer the next step.",
        "Add a primary button in the hero."),
    "nav_complete": ("Conversion", "low", "Footer links to every main section",
        "Consistent footers give a second path to offers and to the privacy policy.",
        "Use the same footer links on every public page."),
}

FOOTER_REQUIRED = ["fearlessly-unfuckwithable.html", "genius-insight.html",
                   "library.html", "about.html", "privacy.html"]


# --------------------------------------------------------------------------- parsing
class PageParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.title = None
        self._in_title = False
        self.metas = []          # dicts
        self.links = []          # <link> dicts
        self.anchors = []        # (attrs, text, in_footer, in_first_section, in_nav)
        self.imgs = []           # (attrs, index_in_main, in_first_section)
        self.headings = []       # (level, text)
        self.jsonld_raw = []
        self.ids = set()
        self.text_parts = []
        self._stack = []
        self._skip_text = 0      # inside script/style/template/hidden
        self._script_type = None
        self._script_buf = []
        self._a = None
        self._h = None
        self._footer = 0
        self._nav = 0
        self._main_sections = 0
        self._in_main = 0
        self._section_depth = []
        self.first_section_open = False
        self.summaries = []
        self._summary = None
        self.has_main = False
        self.main_id = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
            self.title = ""
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
        elif tag == "script":
            self._script_type = a.get("type", "")
            self._script_buf = []
            self._skip_text += 1
        elif tag in ("style", "template", "noscript"):
            self._skip_text += 1
        elif tag == "main":
            self._in_main += 1
            self.has_main = True
            self.main_id = a.get("id")
        elif tag == "footer":
            self._footer += 1
        elif tag in ("nav", "header"):
            self._nav += 1
        elif tag == "section" and self._in_main:
            hidden = "hidden" in a
            self._section_depth.append(hidden)
            if hidden:
                self._skip_text += 1
            self._main_sections += 1
            self.first_section_open = self._main_sections == 1
        elif tag == "a":
            self._a = [a, "", self._footer > 0, self._in_first_section(), self._nav > 0]
            self._a_hidden = self._skip_text > 0
        elif tag == "img":
            self.imgs.append((a, len(self.imgs), self._in_first_section()))
            if self._a is not None and a.get("alt"):
                self._a[1] += a.get("alt")
        elif re.fullmatch(r"h[1-6]", tag):
            self._h = [int(tag[1]), ""]
        elif tag == "summary":
            self._summary = ""
        if tag not in self.VOID:
            self._stack.append(tag)

    def _in_first_section(self):
        return self._in_main > 0 and self._main_sections == 1 and self.first_section_open

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            if "ld+json" in (self._script_type or ""):
                self.jsonld_raw.append("".join(self._script_buf))
            self._skip_text -= 1
            self._script_type = None
        elif tag in ("style", "template", "noscript"):
            self._skip_text -= 1
        elif tag == "main":
            self._in_main -= 1
        elif tag == "footer":
            self._footer -= 1
        elif tag in ("nav", "header"):
            self._nav -= 1
        elif tag == "section" and self._section_depth:
            hidden = self._section_depth.pop()
            if hidden:
                self._skip_text -= 1
            if not self._section_depth:
                self.first_section_open = False
        elif tag == "a" and self._a is not None:
            if not getattr(self, "_a_hidden", False):
                self.anchors.append(tuple(self._a))
            self._a = None
        elif re.fullmatch(r"h[1-6]", tag) and self._h is not None:
            if not self._skip_text:
                self.headings.append((self._h[0], self._h[1].strip()))
            self._h = None
        elif tag == "summary" and self._summary is not None:
            self.summaries.append(self._summary.strip())
            self._summary = None
        if tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass

    def handle_data(self, data):
        if self._script_type is not None:
            self._script_buf.append(data)
            return
        if self._in_title:
            self.title += data
        if self._skip_text:
            return
        if self._a is not None:
            self._a[1] += data
        if self._h is not None:
            self._h[1] += data
        if self._summary is not None:
            self._summary += data
        self.text_parts.append(data)

    # helpers
    def meta(self, key):
        for m in self.metas:
            if m.get("name", "").lower() == key or m.get("property", "").lower() == key:
                return m.get("content", "")
        return None

    def canonical(self):
        for l in self.links:
            if "canonical" in l.get("rel", "").lower().split():
                return l.get("href")
        return None

    @property
    def text(self):
        return re.sub(r"\s+", " ", " ".join(self.text_parts)).strip()


# --------------------------------------------------------------------------- fetching
class Fetcher:
    def __init__(self, base, offline=False):
        self.base = base.rstrip("/")
        self.offline = offline
        self.cache = {}

    def get(self, url, method="GET"):
        key = (url, method)
        if key in self.cache:
            return self.cache[key]
        req = urllib.request.Request(url, method=method, headers={
            "User-Agent": "Mozilla/5.0 (compatible; KJF-SEO-Audit/1.0)"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read() if method == "GET" else b""
                res = (r.status, r.geturl(), body, dict(r.headers))
        except urllib.error.HTTPError as e:
            res = (e.code, url, e.read() if method == "GET" else b"", dict(e.headers or {}))
        except Exception as e:  # network error
            res = (0, url, str(e).encode(), {})
        self.cache[key] = res
        return res


class PagesHandler(http.server.SimpleHTTPRequestHandler):
    """Mimics GitHub Pages: /about -> about.html, real 404 + 404.html, excluded dirs hidden."""

    def log_message(self, *a):
        pass

    def send_head(self):
        path = urllib.parse.urlsplit(self.path).path
        first = path.strip("/").split("/")[0]
        root = self.directory
        fs = os.path.join(root, path.lstrip("/"))
        if (first in UNPUBLISHED_DIRS or first.startswith("_") or first.startswith(".")) and first:
            return self._404()
        if path.endswith("/") and os.path.isfile(os.path.join(fs, "index.html")):
            pass
        elif os.path.isdir(fs) and not path.endswith("/"):
            self.send_response(301)
            self.send_header("Location", path + "/")
            self.end_headers()
            return None
        elif not os.path.exists(fs) and os.path.isfile(fs + ".html"):
            self.path = path + ".html"
        elif not os.path.exists(fs):
            return self._404()
        return super().send_head()

    def _404(self):
        p = os.path.join(self.directory, "404.html")
        body = open(p, "rb").read() if os.path.isfile(p) else b"404"
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        import io
        return io.BytesIO(body)


def serve(root):
    handler = functools.partial(PagesHandler, directory=os.path.abspath(root))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


# --------------------------------------------------------------------------- helpers
def path_of(url):
    p = urllib.parse.urlsplit(url).path or "/"
    return p


def canonical_path(p):
    """The URL form a page should canonicalise to."""
    if p.endswith("/index.html"):
        p = p[: -len("index.html")]
    return p


def walk_jsonld(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk_jsonld(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_jsonld(v)


def types_of(node):
    t = node.get("@type")
    return t if isinstance(t, list) else ([t] if t else [])


REQUIRED = {
    "Person": ["name"],
    "WebSite": ["name", "url"],
    "Book": ["name", "author"],
    "Offer": ["price", "priceCurrency"],
    "Service": ["name", "provider"],
    "FAQPage": ["mainEntity"],
    "Question": ["name", "acceptedAnswer"],
    "Answer": ["text"],
    "BreadcrumbList": ["itemListElement"],
    "ListItem": ["position", "name"],
    "ProfilePage": ["mainEntity"],
}


def price_visible(price, currency, text):
    p = str(price).rstrip("0").rstrip(".") if "." in str(price) else str(price)
    sym = {"USD": "US$", "NZD": "NZ$"}.get(currency, "")
    return bool(re.search(re.escape(sym + p) + r"(?![0-9])", text))


# --------------------------------------------------------------------------- audit
def audit(base, offline=False):
    f = Fetcher(base, offline)
    results = []   # dicts: check, url, passed, detail
    is_live = base.rstrip("/") == SITE

    def rec(check, url, passed, detail=""):
        results.append({"check": check, "url": url, "passed": None if passed is None else bool(passed), "detail": detail})

    def to_site(p):
        return SITE + p

    # robots.txt
    st, _, body, _ = f.get(base + "/robots.txt")
    robots = body.decode("utf-8", "ignore") if st == 200 else ""
    rec("robots_present", "/robots.txt", st == 200, f"HTTP {st}")
    groups, cur = {}, []
    for line in robots.splitlines():
        line = line.split("#")[0].strip()
        if not line or ":" not in line:
            continue
        k, v = [x.strip() for x in line.split(":", 1)]
        if k.lower() == "user-agent":
            if cur and groups.get(cur[-1]) not in (None, []):
                cur = []
            cur.append(v)
            groups.setdefault(v, [])
        elif k.lower() in ("allow", "disallow"):
            for ua in cur:
                groups.setdefault(ua, []).append((k.lower(), v))
    star_block = any(k == "disallow" and v == "/" for k, v in groups.get("*", []))
    rec("robots_allows_site", "/robots.txt", not star_block, "Disallow: / for *" if star_block else "")
    sitemap_lines = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots)
    rec("robots_sitemap", "/robots.txt", any(s.endswith("/sitemap.xml") for s in sitemap_lines),
        ", ".join(sitemap_lines) or "no Sitemap line")
    blocked_ai = [ua for ua in AI_CRAWLERS
                  if any(k == "disallow" and v == "/" for k, v in groups.get(ua, []))]
    rec("ai_crawlers_allowed", "/robots.txt", not blocked_ai and not star_block,
        ("blocked: " + ", ".join(blocked_ai)) if blocked_ai else ("no robots.txt: allowed by default" if st != 200 else ""))

    # sitemap
    st, _, body, _ = f.get(base + "/sitemap.xml")
    sitemap_paths = []
    ok = False
    if st == 200:
        try:
            root = ET.fromstring(body)
            ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            locs = [e.text.strip() for e in root.findall(".//s:loc", ns)]
            ok = bool(locs) and all(l.startswith(SITE + "/") for l in locs)
            sitemap_paths = [path_of(l) for l in locs]
        except ET.ParseError as e:
            ok = False
    rec("sitemap_present", "/sitemap.xml", ok, f"HTTP {st}, {len(sitemap_paths)} URLs")

    # llms.txt
    st, _, body, _ = f.get(base + "/llms.txt")
    llms_ok = st == 200 and body.strip().startswith(b"#")
    rec("llms_txt", "/llms.txt", llms_ok, f"HTTP {st}")

    # 404 behaviour
    st, _, body, _ = f.get(base + "/this-page-does-not-exist-kjf-audit")
    rec("not_found_status", "/this-page-does-not-exist-kjf-audit", st == 404, f"HTTP {st}")

    # crawl
    seen, queue, pages = set(), ["/"] + list(sitemap_paths), {}
    llms_links = re.findall(r"\((https://kayjoyflowers\.online[^)\s]*)\)", body.decode("utf-8", "ignore")) if llms_ok else []
    inlinks = {}
    while queue:
        p = queue.pop(0)
        if p in seen:
            continue
        seen.add(p)
        st, final, body, hdr = f.get(base + p)
        ctype = {k.lower(): v for k, v in hdr.items()}.get("content-type", "")
        if st != 200 or "html" not in ctype:
            pages[p] = {"status": st, "parser": None, "html": b""}
            continue
        pr = PageParser()
        pr.feed(body.decode("utf-8", "ignore"))
        pages[p] = {"status": st, "parser": pr, "html": body}
        for a, _t, _foot, _first, _nav in pr.anchors:
            href = a.get("href", "")
            if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            absu = urllib.parse.urljoin(base + p, href)
            u = urllib.parse.urlsplit(absu)
            if absu.startswith(base) or u.netloc == "kayjoyflowers.online":
                tp = u.path or "/"
                inlinks.setdefault(tp, set()).add(p)
                if tp not in seen:
                    queue.append(tp)
    for p in PRIVATE_PATHS:
        if p not in pages:
            st, final, body, hdr = f.get(base + p)
            pr = None
            if st == 200:
                pr = PageParser()
                pr.feed(body.decode("utf-8", "ignore"))
            pages[p] = {"status": st, "parser": pr, "html": body}

    def is_noindex(pr):
        return pr is not None and "noindex" in (pr.meta("robots") or "").lower()

    # private pages
    for p in PRIVATE_PATHS:
        pg = pages.get(p)
        if pg and pg["status"] == 200:
            rec("private_noindex", p, is_noindex(pg["parser"]) and p not in sitemap_paths,
                "noindex" if is_noindex(pg["parser"]) else "indexable")

    indexable = {p: pg for p, pg in pages.items()
                 if pg["status"] == 200 and pg["parser"] is not None and not is_noindex(pg["parser"])
                 and p not in PRIVATE_PATHS}
    # collapse /index.html into /
    if "/index.html" in indexable and "/" in indexable:
        indexable.pop("/index.html")

    # sitemap completeness/cleanliness
    for p in indexable:
        cp = canonical_path(p)
        rec("sitemap_complete", p, cp in sitemap_paths, "" if cp in sitemap_paths else "missing from sitemap")
    for sp in sitemap_paths:
        pg = pages.get(sp)
        good = pg and pg["status"] == 200 and pg["parser"] and not is_noindex(pg["parser"])
        if good:
            can = pg["parser"].canonical()
            good = can == to_site(sp)
        rec("sitemap_clean", sp, good, "" if good else "non-200, noindex or not self-canonical")

    # statuses for every internal link target
    titles, descs, persons = {}, {}, []
    for p, pg in sorted(pages.items()):
        if pg["status"] != 200 and p not in PRIVATE_PATHS:
            rec("status_ok", p, False, f"HTTP {pg['status']}; linked from {sorted(inlinks.get(p, []))}")

    for p, pg in sorted(indexable.items()):
        pr = pg["parser"]
        rec("status_ok", p, True)
        # canonical
        can = pr.canonical()
        rec("canonical_present", p, bool(can), can or "")
        expected = to_site(canonical_path(p))
        rec("canonical_self", p, can == expected, f"{can} (expected {expected})")
        rec("viewport", p, "width=device-width" in (pr.meta("viewport") or ""))
        rec("lang", p, bool(pr.lang), pr.lang or "missing")
        # metadata
        t = (pr.title or "").strip()
        rec("title_present", p, bool(t), t)
        rec("title_length", p, 15 <= len(t) <= 65, f"{len(t)} chars: {t}")
        titles.setdefault(t, []).append(p)
        d = (pr.meta("description") or "").strip()
        rec("desc_present", p, bool(d))
        rec("desc_length", p, 70 <= len(d) <= 160, f"{len(d)} chars")
        descs.setdefault(d, []).append(p)
        og = {k: pr.meta("og:" + k) for k in ("title", "description", "image", "url", "type")}
        missing = [k for k, v in og.items() if not v]
        rec("og_complete", p, not missing, "missing og:" + ", og:".join(missing) if missing else "")
        if og["url"]:
            rec("og_url_canonical", p, og["url"] == can, og["url"])
        img_url = og["image"] or ""
        if img_url.startswith(SITE + "/") and base != SITE:
            img_url = base + img_url[len(SITE):]   # local run: check the local copy
        if img_url and (not offline or img_url.startswith(base)):
            st, *_ = f.get(img_url, "HEAD")
            rec("og_image_ok", p, st == 200, f"HTTP {st}")
        rec("twitter_card", p, bool(pr.meta("twitter:card")))
        # headings / content
        h1s = [h for h in pr.headings if h[0] == 1]
        rec("h1_single", p, len(h1s) == 1, f"{len(h1s)} H1: " + " | ".join(h[1] for h in h1s))
        skips, prev = [], 0
        for lvl, txt in pr.headings:
            if prev and lvl > prev + 1:
                skips.append(f"H{prev}→H{lvl} ('{txt[:40]}')")
            prev = lvl
        rec("heading_order", p, not skips, "; ".join(skips))
        wc = len(re.findall(r"\b[\w'’-]+\b", pr.text))
        if p != "/privacy.html":
            rec("word_count", p, wc >= 250, f"{wc} words")
        # JSON-LD
        nodes, valid = [], True
        for raw in pr.jsonld_raw:
            try:
                nodes.extend(walk_jsonld(json.loads(raw)))
            except json.JSONDecodeError as e:
                valid = False
        rec("jsonld_present", p, bool(pr.jsonld_raw), f"{len(pr.jsonld_raw)} block(s)")
        if pr.jsonld_raw:
            rec("jsonld_valid", p, valid)
            missing = []
            for n in nodes:
                for t_ in types_of(n):
                    for prop in REQUIRED.get(t_, []):
                        if prop not in n:
                            missing.append(f"{t_}.{prop}")
            rec("jsonld_required", p, not missing, ", ".join(sorted(set(missing))))
            bad = []
            for n in nodes:
                if "Offer" in types_of(n) and "price" in n:
                    if not price_visible(n["price"], n.get("priceCurrency", ""), pr.text):
                        bad.append(f"{n.get('priceCurrency')} {n['price']}")
            if any("Offer" in types_of(n) for n in nodes):
                rec("jsonld_prices_visible", p, not bad, "not visible: " + ", ".join(bad) if bad else "")
            qs = [n.get("name", "") for n in nodes if "Question" in types_of(n)]
            if qs:
                vis = set(s.strip() for s in pr.summaries) | set(h[1] for h in pr.headings)
                miss = [q for q in qs if q not in vis and q not in pr.text]
                rec("faq_visible", p, not miss, "; ".join(miss))
            for n in nodes:
                if "Person" in types_of(n):
                    persons.append((p, n.get("@id"), n.get("name")))
        if canonical_path(p) != "/":
            has_bc = any("BreadcrumbList" in types_of(n) for n in nodes)
            rec("breadcrumbs", p, has_bc)
        author = pr.meta("author") or any("author" in n or "Person" in types_of(n) for n in nodes)
        rec("author_attribution", p, bool(author))
        # links
        broken, anchors_bad = [], []
        for a, txt, foot, first, nav in pr.anchors:
            href = a.get("href", "")
            if href.startswith("#"):
                if len(href) > 1 and href[1:] not in pr.ids:
                    anchors_bad.append(href)
                continue
            if not href or href.startswith(("mailto:", "tel:")):
                continue
            absu = urllib.parse.urljoin(base + p, href)
            u = urllib.parse.urlsplit(absu)
            if absu.startswith(base):
                tp = u.path or "/"
                tpg = pages.get(tp)
                if not tpg or tpg["status"] != 200:
                    broken.append(href)
                elif u.fragment and tpg["parser"] and u.fragment not in tpg["parser"].ids:
                    anchors_bad.append(href)
        rec("internal_links_ok", p, not broken, ", ".join(sorted(set(broken))))
        rec("anchors_ok", p, not anchors_bad, ", ".join(sorted(set(anchors_bad))))
        others = [s for s in inlinks.get(p, set()) | (inlinks.get("/index.html", set()) if p == "/" else set())
                  if s != p and s in indexable]
        if canonical_path(p) != "/":
            rec("not_orphan", p, bool(others), f"linked from {len(others)} page(s)")
        # accessibility
        bad_alt = [i[0].get("src", "")[-40:] for i in pr.imgs
                   if not i[0].get("alt", "").strip() and i[0].get("role") != "presentation"]
        rec("img_alt", p, not bad_alt, f"{len(bad_alt)} image(s) without alt text" if bad_alt else f"{len(pr.imgs)} images")
        no_text = [a.get("href") for a, txt, *_ in pr.anchors if not txt.strip() and not a.get("aria-label")]
        rec("link_text", p, not no_text, ", ".join(no_text))
        skip = any(a.get("href", "").startswith("#") and a.get("href")[1:] == (pr.main_id or "\0")
                   for a, *_ in pr.anchors)
        rec("skip_link", p, skip)
        # performance
        nodim = [i[0].get("src", "")[-40:] for i in pr.imgs if not (i[0].get("width") and i[0].get("height"))]
        if pr.imgs:
            rec("img_dimensions", p, not nodim, f"{len(nodim)} of {len(pr.imgs)} images without width/height")
        first_imgs = [i for i in pr.imgs if i[2]]
        if first_imgs:
            lazy = first_imgs[0][0].get("loading") == "lazy"
            rec("lcp_not_lazy", p, not lazy, "hero image has loading=lazy" if lazy else "")
        rec("html_weight", p, len(pg["html"]) < 100_000, f"{len(pg['html'])/1024:.1f} KB")
        # conversion
        hero_cta = any(first and "btn" in a.get("class", "") for a, txt, foot, first, nav in pr.anchors)
        if canonical_path(p) not in ("/privacy.html", "/about.html"):
            rec("hero_cta", p, hero_cta)
        foot = {urllib.parse.urlsplit(a.get("href", "")).path for a, txt, infoot, *_ in pr.anchors if infoot}
        own = p.lstrip("/")
        missing_f = [r for r in FOOTER_REQUIRED if r not in foot and r != own]
        rec("nav_complete", p, not missing_f, "footer missing: " + ", ".join(missing_f) if missing_f else "")
        if not offline:
            dead, unverified = [], []
            for a, *_ in pr.anchors:
                href = a.get("href", "")
                if urllib.parse.urlsplit(href).netloc in CHECKOUT_HOSTS:
                    st, final, body_, hdrs = f.get(href)
                    server = {k.lower(): v for k, v in hdrs.items()}.get("server", "")
                    if st == 403 and "cloudflare" in server.lower():
                        unverified.append(href)
                    elif st != 200:
                        dead.append(f"{href} → HTTP {st}")
            for u_ in sorted(set(unverified)):
                rec("checkout_links_ok", p, None, f"{u_} → bot protection (HTTP 403); verify in a browser")
            checkout = [a.get("href") for a, *_ in pr.anchors
                        if urllib.parse.urlsplit(a.get("href", "")).netloc in CHECKOUT_HOSTS]
            checkout = [c for c in checkout if c not in unverified]
            if checkout:
                rec("checkout_links_ok", p, not dead, "; ".join(dead) or f"{len(set(checkout))} unique checkout link(s) OK")

    # uniqueness
    for t, ps in titles.items():
        for p in ps:
            rec("title_unique", p, len(ps) == 1, "shared with " + ", ".join(x for x in ps if x != p) if len(ps) > 1 else "")
    for d, ps in descs.items():
        if d:
            for p in ps:
                rec("desc_unique", p, len(ps) == 1, "")
    # entities
    home = indexable.get("/")
    if home:
        hn = []
        for raw in home["parser"].jsonld_raw:
            try:
                hn.extend(walk_jsonld(json.loads(raw)))
            except json.JSONDecodeError:
                pass
        has = {t for n in hn for t in types_of(n)}
        rec("entity_home", "/", {"WebSite", "Person"} <= has or {"WebSite", "Organization"} <= has,
            "types: " + ", ".join(sorted(has)) if has else "no JSON-LD")
    if persons:
        ids = {(i, n) for _, i, n in persons if i}
        rec("entity_consistent", "/", len({i for i, _ in ids}) <= 1 and len({n for _, n in ids}) <= 1,
            "; ".join(f"{i} = {n}" for i, n in sorted(ids)))

    return summarise(results, pages, indexable, sitemap_paths, base, offline)


def summarise(results, pages, indexable, sitemap_paths, base, offline):
    cats = {c: {"earned": 0, "possible": 0, "passed": 0, "failed": 0} for c in CATEGORIES}
    for r in results:
        cat, sev, *_ = CHECKS[r["check"]]
        w = SEVERITY_WEIGHT[sev]
        r.update({"category": cat, "severity": sev, "title": CHECKS[r["check"]][2]})
        if r["passed"] is None:
            cats[cat].setdefault("unverified", 0)
            cats[cat]["unverified"] += 1
            continue
        cats[cat]["possible"] += w
        if r["passed"]:
            cats[cat]["earned"] += w
            cats[cat]["passed"] += 1
        else:
            cats[cat]["failed"] += 1
    for c in cats.values():
        c["score"] = round(100 * c["earned"] / c["possible"]) if c["possible"] else None
    tot_e = sum(c["earned"] for c in cats.values())
    tot_p = sum(c["possible"] for c in cats.values())
    return {
        "base": base,
        "offline": offline,
        "overall": round(100 * tot_e / tot_p) if tot_p else None,
        "categories": cats,
        "checks": {k: {"category": v[0], "severity": v[1], "title": v[2], "principle": v[3], "fix": v[4]}
                   for k, v in CHECKS.items()},
        "results": results,
        "pages": {p: {"status": pg["status"], "indexable": p in indexable,
                      "title": (pg["parser"].title or "").strip() if pg["parser"] else None,
                      "words": len(re.findall(r"\b[\w'’-]+\b", pg["parser"].text)) if pg["parser"] else 0,
                      "bytes": len(pg["html"])}
                  for p, pg in sorted(pages.items())},
        "sitemap": sitemap_paths,
    }


def grade(score):
    if score is None:
        return "–"
    return "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--base", help="site URL, e.g. https://kayjoyflowers.online")
    g.add_argument("--root", help="local folder to serve like GitHub Pages")
    ap.add_argument("--json", help="write full results to this file")
    ap.add_argument("--offline", action="store_true", help="skip external checks")
    ap.add_argument("--fail-on", choices=SEVERITY_ORDER, help="exit 1 if a check this severe or worse fails")
    args = ap.parse_args()

    httpd = None
    base = args.base
    if args.root:
        httpd, base = serve(args.root)
    try:
        res = audit(base.rstrip("/"), offline=args.offline)
    finally:
        if httpd:
            httpd.shutdown()
    if args.root:
        res["base"] = f"local:{os.path.abspath(args.root)}"

    print(f"\nSEO/AEO audit of {res['base']}")
    print(f"Overall {res['overall']}/100 ({grade(res['overall'])})")
    for c, v in res["categories"].items():
        if v["possible"]:
            print(f"  {c:<20} {v['score']:>3}/100 ({grade(v['score'])})  {v['passed']} passed, {v['failed']} failed")
    fails = [r for r in res["results"] if r["passed"] is False]
    unv = [r for r in res["results"] if r["passed"] is None]
    fails.sort(key=lambda r: (SEVERITY_ORDER.index(r["severity"]), r["check"], r["url"]))
    if fails:
        print("\nFailed checks:")
        for r in fails:
            print(f"  [{r['severity']:<8}] {r['title']} — {r['url']}" + (f"  ({r['detail']})" if r["detail"] else ""))
    if unv:
        print("\nNot verifiable automatically (not scored):")
        for r in unv:
            print(f"  {r['title']} — {r['url']}  ({r['detail']})")
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(res, fh, indent=1)
        print(f"\nWrote {args.json}")
    if args.fail_on:
        limit = SEVERITY_ORDER.index(args.fail_on)
        if any(SEVERITY_ORDER.index(r["severity"]) <= limit for r in fails):
            print(f"\nFAIL: at least one {args.fail_on}-or-worse check failed.")
            sys.exit(1)


if __name__ == "__main__":
    main()
