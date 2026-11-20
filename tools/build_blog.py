#!/usr/bin/env python3
"""Build the Journal (blog) pages from Markdown.

Sources (kept out of the published site by _config.yml):
  content/blog/articles/*.md      article text with YAML front matter (approved copy, published as written)
  content/blog/metadata/*.json    editorial metadata, incl. a base BlogPosting JSON-LD object
  content/blog/published.json     {"slug": "YYYY-MM-DD"} publication dates (and optional "updated")

Output:
  blog/index.html                 the Journal index
  blog/<slug>/index.html          one page per article (URL /blog/<slug>/)

Usage:  python3 tools/build_blog.py          (needs: pip install markdown==3.7)
Then:   add share images to tools/og-images.json, run node tools/make_images.mjs images/og/blog-*.jpg,
        commit, run python3 tools/build_sitemap.py, commit sitemap.xml.

The article text is never rewritten. The build only: drops the front matter, turns site links into
root-relative links, marks the byline, adds the visible date, renders the closing call-to-action link
as a button, styles the author note, and wraps tables so they scroll on phones.
"""
import datetime
import glob
import html
import json
import os
import re
from urllib.parse import parse_qsl, urlencode, urlsplit

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content", "blog")
SITE = "https://kayjoyflowers.online"
CSS_VERSION = "12"
KAY = "https://kayjoyflowers.online/#kay"

FONTS = ('\n'
         '\n'
         '<link rel="stylesheet" href="/fonts/fonts.css?v=1">\n'
         f'<link rel="stylesheet" href="/styles.css?v={CSS_VERSION}">\n'
         '<link rel="icon" href="/favicon.ico" sizes="48x48">\n'
         '<link rel="icon" href="/images/icon-192.png" type="image/png" sizes="192x192">\n'
         '<link rel="apple-touch-icon" href="/apple-touch-icon.png">')

NAV = [("/", "Home"), ("/fearlessly-unfuckwithable.html", "Fearlessly Unfuckwithable"),
       ("/genius-insight.html", "Energetic Scans"), ("/library.html", "The Library"),
       ("/blog/", "Journal"), ("/podcast/", "Podcast"), ("/about.html", "About")]

E = html.escape


# Podcast episodes that discuss an essay; the player is inserted into that essay.
LISTEN = {
    "who-are-you-beyond-your-roles": '<h2>Listen to the conversation</h2>\n<p>This essay is the subject of the first episode of the <a href="/podcast/">Living Cosmology of Remembrance</a> podcast. Two AI hosts, Iris and Jonah, talk it through, quoting the essay word for word.</p>\n<audio controls preload="none" src="/podcast/audio/s01e001.mp3" style="width:100%;margin:6px 0"></audio>\n<p class="muted"><a href="/podcast/s01e001/">Show notes, chapters and transcript</a></p>\n',
}


def header(current):
    links = "\n".join(f'    <a href="{h}"{" aria-current=\"page\"" if h == current else ""}>{t}</a>' for h, t in NAV)
    return ('<a class="skip" href="#main">Skip to content</a>\n<header class="site"><div class="wrap">\n'
            '  <a class="logo" href="/"><img src="/images/kjf-logo-96.png" width="44" height="44" alt="KJF monogram">Kay Joy Flowers</a>\n  <nav class="main">\n' + links + '\n  </nav>\n</div></header>')


FOOTER = ('<footer class="site"><div class="wrap">\n'
          '  <div>&copy; Kay Joy Flowers. A Living Cosmology of Remembrance.<br><a href="mailto:kay@kayjoyflowers.online">kay@kayjoyflowers.online</a></div>\n'
          '  <div><a href="/">Home</a> &middot; <a href="/fearlessly-unfuckwithable.html">Fearlessly Unfuckwithable</a> &middot; '
          '<a href="/genius-insight.html">Energetic Scans</a> &middot; <a href="/library.html">The Library</a> &middot; '
          '<a href="/blog/">Journal</a> &middot; <a href="/about.html">About</a> &middot; <a href="/privacy.html">Privacy</a></div>\n'
          '</div></footer>')


def nice_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def parse(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    fm = {}
    for line in m.group(1).splitlines():
        k, v = line.split(":", 1)
        fm[k.strip()] = json.loads(v.strip())   # values are JSON-compatible strings and arrays
    return fm, text[m.end():]


def head(title, desc, canonical, og_type, og_image, og_alt, ld, extra=""):
    return f"""<!DOCTYPE html>
<html lang="en-NZ">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:site_name" content="Kay Joy Flowers">
<meta property="og:locale" content="en_NZ">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{E(og_alt)}">
{extra}<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<meta name="twitter:image" content="{og_image}">
<meta name="twitter:image:alt" content="{E(og_alt)}">
<meta name="author" content="Kay Joy Flowers">
<script type="application/ld+json">
{json.dumps(ld, indent=1, ensure_ascii=False)}
</script>
{FONTS}
</head>
<body>
"""


def render_body(md, fm, published):
    body = markdown.markdown(md, extensions=["tables"], output_format="html")
    # site links become root-relative so they work on any host
    body = body.replace(f'href="{SITE}/', 'href="/')
    # byline + visible date
    body, n = re.subn(r'<p>By <a href="/about.html">Kay Joy Flowers</a></p>',
                      '<p class="byline">By <a href="/about.html">Kay Joy Flowers</a></p>\n'
                      f'<p class="postmeta">Published <time datetime="{published}">{nice_date(published)}</time></p>', body, count=1)
    assert n == 1, f"{fm['slug']}: byline not found"
    # closing call to action: the paragraph that is only the CTA link
    cta = fm["primary_cta_url"].replace(SITE, "")
    pat = re.compile(r'<p><a href="' + re.escape(cta) + r'">' + re.escape(E(fm["primary_cta_text"], quote=False)) + r'</a>\.?</p>')
    destination = urlsplit(cta)
    query = urlencode(dict(parse_qsl(destination.query)) | {
        "utm_source": "journal", "utm_medium": "website", "utm_content": fm["slug"],
    })
    tracked_cta = E(destination._replace(query=query).geturl())
    body, n = pat.subn(f'<p class="cta"><a class="btn primary" href="{tracked_cta}">{E(fm["primary_cta_text"], quote=False)}</a></p>', body)
    assert n == 1, f"{fm['slug']}: CTA paragraph not found"
    # author note (the final italic paragraph)
    body, n = re.subn(r'<p><em>(Kay Joy Flowers is [^<]*)</em></p>\s*$', r'<p class="bio"><em>\1</em></p>', body.rstrip())
    assert n == 1, f"{fm['slug']}: author note not found"
    body = body.replace("<table>", '<div class="tablewrap"><table>').replace("</table>", "</table></div>")
    return body


def first_answer(md):
    """The opening paragraph after the byline: the article's direct answer (used as the index excerpt)."""
    paras = [p.strip() for p in md.split("\n\n") if p.strip()]
    i = next(i for i, p in enumerate(paras) if p.startswith("By [Kay Joy Flowers]"))
    return paras[i + 1]


def hero_img(slug, heroes, sizes, cls, eager):
    """<img> for an article's hero image (content/blog/heroes.json), or "" if it has none."""
    h = heroes.get(slug)
    if not h:
        return ""
    srcset = ", ".join(f'/images/blog/{h["name"]}-{w}.webp {w}w' for w in h["widths"])
    w, ht = h["full"]
    load = 'fetchpriority="high" decoding="async"' if eager else 'loading="lazy" decoding="async"'
    return (f'<img class="{cls}" src="/images/blog/{h["name"]}-{h["widths"][0]}.webp" srcset="{srcset}" sizes="{sizes}" '
            f'width="{w}" height="{ht}" alt="{E(h["alt"])}" {load}>')


def main():
    dates = json.load(open(os.path.join(SRC, "published.json")))
    hp = os.path.join(SRC, "heroes.json")
    heroes = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else {}
    meta = {}
    for f in glob.glob(os.path.join(SRC, "metadata", "*.json")):
        m = json.load(open(f, encoding="utf-8"))
        meta[m["slug"]] = m
    posts = []
    for f in sorted(glob.glob(os.path.join(SRC, "articles", "*.md"))):
        fm, md = parse(f)
        slug = fm["slug"]
        if slug not in dates:
            print(f"skip (no publication date): {slug}")
            continue
        posts.append((fm, md, meta[slug]))

    for fm, md, m in posts:
        slug = fm["slug"]
        d = dates[slug]
        published = d if isinstance(d, str) else d["published"]
        updated = published if isinstance(d, str) else d.get("updated", published)
        url = f"{SITE}/blog/{slug}/"
        og = f"{SITE}/images/og/blog-{slug}.jpg"
        base = dict(m["structured_data_recommendation"]["base_json_ld"])
        base.pop("@context", None)
        posting = {"@type": "BlogPosting", "@id": url + "#article", "headline": base["headline"],
                   "description": base["description"],
                   "author": {"@type": "Person", "@id": KAY, "name": "Kay Joy Flowers", "url": f"{SITE}/about.html"},
                   "publisher": {"@id": KAY},
                   "datePublished": published, "dateModified": updated,
                   "url": url, "mainEntityOfPage": url, "image": og,
                   "inLanguage": base.get("inLanguage", "en-NZ"),
                   "isAccessibleForFree": base.get("isAccessibleForFree", True),
                   "articleSection": base.get("articleSection"), "keywords": base.get("keywords"),
                   "isPartOf": {"@id": f"{SITE}/blog/#journal"}}
        ld = {"@context": "https://schema.org", "@graph": [posting, {
            "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
                {"@type": "ListItem", "position": 2, "name": "Journal", "item": f"{SITE}/blog/"},
                {"@type": "ListItem", "position": 3, "name": fm["title"], "item": url}]}]}
        extra = (f'<meta property="article:published_time" content="{published}">\n'
                 f'<meta property="article:modified_time" content="{updated}">\n'
                 f'<meta property="article:author" content="{SITE}/about.html">\n')
        others = "\n".join(f'    <li><a href="/blog/{o["slug"]}/">{E(o["title"], quote=False)}</a></li>'
                           for o, _, _ in posts if o["slug"] != slug)
        og_alt = heroes[slug]["alt"] if slug in heroes else f'{fm["title"]} By Kay Joy Flowers.'
        body = render_body(md, fm, published)
        if slug in LISTEN:  # podcast player before the closing "Explore" section
            body = body.replace("<h2>Explore A Living Cosmology", LISTEN[slug] + "<h2>Explore A Living Cosmology", 1)
        hero = hero_img(slug, heroes, "(min-width: 760px) 712px, calc(100vw - 48px)", "heroimg", True)
        if hero:
            # hero image right after the byline and date, before the opening answer
            body = body.replace('</time></p>', '</time></p>\n<figure class="posthero">' + hero + '</figure>', 1)
        page = (head(fm["seo_title"], fm["description"], url, "article", og, og_alt, ld, extra)
                + header("/blog/") + '\n\n<main id="main">\n<article class="post"><div class="wrap narrow prose">\n'
                + '<p class="eyebrow"><a href="/blog/">Journal</a></p>\n'
                + body
                + '\n</div></article>\n\n<section class="related"><div class="wrap narrow">\n'
                + '  <p class="eyebrow">More from the Journal</p>\n  <ul class="postlinks">\n' + others + '\n  </ul>\n</div></section>\n</main>\n\n'
                + FOOTER + "\n</body>\n</html>\n")
        out = os.path.join(ROOT, "blog", slug, "index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", encoding="utf-8").write(page)
        print("wrote", os.path.relpath(out, ROOT))

    # index
    url = f"{SITE}/blog/"
    title = "Journal | Kay Joy Flowers"
    desc = ("Articles by Kay Joy Flowers on sovereignty, the body and remembering who you are: "
            "bracing, receiving, overwhelm, identity, frequency and teaching.")
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Blog", "@id": url + "#journal", "name": "Journal", "url": url, "description": desc,
         "inLanguage": "en-NZ", "author": {"@id": KAY}, "publisher": {"@id": KAY},
         "blogPost": [{"@id": f"{SITE}/blog/{fm['slug']}/#article"} for fm, _, _ in posts]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "Journal", "item": url}]}]}
    cards = []
    for fm, md, m in posts:
        d = dates[fm["slug"]]
        published = d if isinstance(d, str) else d["published"]
        excerpt = markdown.markdown(first_answer(md), output_format="html").replace(f'href="{SITE}/', 'href="/')
        img = hero_img(fm["slug"], heroes, "(min-width: 760px) 712px, calc(100vw - 48px)", "postcardimg", False)
        img = f'<a class="cardlink" href="/blog/{fm["slug"]}/" tabindex="-1" aria-hidden="true">{img}</a>\n    ' if img else ""
        cards.append(f'''  <article class="postcard">
    {img}<p class="postmeta"><time datetime="{published}">{nice_date(published)}</time></p>
    <h2><a href="/blog/{fm["slug"]}/">{E(fm["title"], quote=False)}</a></h2>
    {excerpt}
    <p class="more"><a href="/blog/{fm["slug"]}/" aria-label="Read the article: {E(fm["title"])}">Read the article</a></p>
  </article>''')
    page = (head(title, desc, url, "website", f"{SITE}/images/og/blog.jpg",
                 "Journal: articles by Kay Joy Flowers.", ld)
            + header("/blog/") + '\n\n<main id="main">\n<section class="hero"><div class="wrap narrow">\n'
            + '  <p class="eyebrow">Journal</p>\n  <h1>Journal</h1>\n'
            + '  <p class="lede">Articles by Kay Joy Flowers on sovereignty, the body and remembering who you are.</p>\n'
            + '</div></section>\n\n<section style="padding-top:0"><div class="wrap narrow">\n<div class="postlist">\n'
            + "\n".join(cards) + '\n</div>\n</div></section>\n</main>\n\n' + FOOTER + "\n</body>\n</html>\n")
    open(os.path.join(ROOT, "blog", "index.html"), "w", encoding="utf-8").write(page)
    print("wrote blog/index.html")


if __name__ == "__main__":
    main()
