#!/usr/bin/env python3
"""Build the Living Cosmology of Remembrance podcast pages and RSS feed.

One feed for the whole podcast; each series is a season. To add an episode: put the MP3 in
podcast/audio/, the artwork and chapters.json in podcast/<slug>/, the transcript in
content/podcast/<slug>_transcript.txt, add an entry to EPISODES, then run:
  python3 tools/build_podcast.py
Writes podcast/index.html, podcast/<slug>/index.html (show notes + transcript) and podcast/feed.xml.
Hosts are AI voices; every page and feed item says so.
"""
import html, json, os, re, uuid
from datetime import datetime, timezone
from email.utils import format_datetime

SITE = "https://kayjoyflowers.online"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED_URL = f"{SITE}/podcast/feed.xml"
OP3 = "https://op3.dev/e/"  # free, open podcast download analytics (prefix redirect)
TITLE = "Living Cosmology of Remembrance"
AUTHOR = "Kay Joy Flowers"
EMAIL = "kay@kayjoyflowers.online"
SHOW_DESC = ("The podcast of A Living Cosmology of Remembrance, created by author Kay Joy Flowers. "
             "Each series explores one of her books or bodies of work through a conversation between two AI hosts, "
             "Iris and Jonah. The ideas and every quotation are Kay's; the hosts are AI voices and never speak as her. "
             "Series One: Who ARE You?")
SERIES = {1: "Who ARE You?"}
UTM = "utm_source=podcast&utm_medium=audio&utm_campaign={camp}&utm_content={content}"

EPISODES = [
    {
        "slug": "s01e001", "season": 1, "episode": 1, "explicit": True,
        "title": "Who Are You Beneath the Roles You've Been Playing?",
        "published": "2026-11-20T14:30:00+13:00",
        "duration": 642, "bytes": 10277543,
        "summary": ("Two AI hosts explore Kay Joy Flowers' essay on the roles we play, the rules that attach "
                    "themselves to them, and a simple “I am” exercise for making room for your own voice."),
        "essay": "/blog/who-are-you-beyond-your-roles/",
        "essay_title": "Who Are You Beneath the Roles You've Been Playing?",
        "book": "/fearlessly-unfuckwithable.html", "book_title": "Fearlessly Unfuckwithable",
        "notes_intro": [
            "Who are you when you are not explaining your usefulness?",
            "In the first episode of Series One, Who ARE You?, AI hosts Iris and Jonah talk through Kay Joy Flowers' "
            "Journal essay. They look at why a meaningful role can still become too small, what Kay means by "
            "remembrance, where this question sits among the seven gateways of A Living Cosmology of Remembrance, "
            "and the difference between a role and the rule that attaches itself to it.",
        ],
        "try_this": "Finish the sentence “To be allowed to remain this person, I believe I have to…”, then ask whether you chose that condition.",
    },
]


def esc(s): return html.escape(s, quote=True)
def hms(t): t = int(round(t)); return f"{t // 60}:{t % 60:02d}"
def utm(path, camp, content): return f"{path}?{UTM.format(camp=camp, content=content)}"


def head(title, desc, canonical, og_image, og_alt, jsonld, og_type="website"):
    return f"""<!DOCTYPE html>
<html lang="en-NZ">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" type="application/rss+xml" title="{esc(TITLE)} (podcast feed)" href="{FEED_URL}">
<meta property="og:site_name" content="Kay Joy Flowers">
<meta property="og:locale" content="en_NZ">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:alt" content="{esc(og_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og_image}">
<meta name="author" content="Kay Joy Flowers">
<script type="application/ld+json">
{json.dumps(jsonld, indent=1, ensure_ascii=False)}
</script>
<link rel="stylesheet" href="/fonts/fonts.css?v=1">
<link rel="stylesheet" href="/styles.css?v=12">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/images/icon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<style>
.player{{width:100%;margin:10px 0 6px}}
main section.listen{{border-top:0;padding:56px 0;background:radial-gradient(circle at 18% 25%,#6b3249 0%,#3a1a31 45%,#1f1020 100%);color:#fbefe0}}
.listen .lgrid{{display:grid;grid-template-columns:minmax(240px,380px) 1fr;gap:44px;align-items:center}}
.listen .art{{width:100%;height:auto;aspect-ratio:1;object-fit:cover;align-self:center;border-radius:18px;display:block;box-shadow:0 22px 55px #0009,0 0 0 1px #e0b26a66}}
.listen .eyebrow{{color:#e6b56f;letter-spacing:.16em}}
.listen .eyebrow a{{color:#e6b56f;text-decoration:none}}
.listen h1{{color:#fff6ea;margin:0 0 10px;font-size:clamp(32px,4.2vw,50px);line-height:1.12}}
.listen .lede{{color:#f6e6d4;margin:0 0 20px;font-size:clamp(18px,2vw,22px)}}
.listen .byline{{color:#efdccd;font-size:16px}}
.listen .byline a,.listen .elinks a{{color:#f0c27e}}
.epcard{{background:#ffffff0f;border:1px solid #e0b26a55;border-radius:16px;padding:18px 20px 12px;margin-top:6px}}
.epcard .k{{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#f0c27e;margin:0 0 4px;font-weight:600}}
.epcard h2{{font-size:clamp(24px,2.6vw,30px);font-weight:600;color:#fff8ee;margin:2px 0 4px;line-height:1.2}}
.epcard h2 a{{color:#fff6ea;text-decoration:none}}
.epcard p{{margin:0}}
.elinks{{font-size:15px;color:#efdccd;margin:4px 0 0}}
.listen .player{{color-scheme:dark;margin:14px 0 8px}}
main section.after{{border-top:0;padding:44px 0 64px}}
@media (max-width:760px){{main section.listen{{padding:32px 0 36px}}.listen .lgrid{{grid-template-columns:1fr;gap:24px}}.listen .art{{max-width:240px;margin:0 auto}}}}
.aidisc{{font-size:15px;color:var(--muted);border-left:3px solid var(--accent);padding:4px 0 4px 14px;margin:18px 0}}
.chapters{{list-style:none;padding:0;margin:8px 0 20px}}
.chapters li{{display:flex;gap:14px;padding:4px 0;border-bottom:1px solid var(--line)}}
.chapters .t{{font-variant-numeric:tabular-nums;color:var(--muted);min-width:44px}}
.transcript p{{margin:0 0 10px}}
.transcript .who{{font-weight:600;color:var(--accent)}}
.eplist{{list-style:none;padding:0}}
.eplist li{{border:1px solid var(--line);border-radius:14px;padding:20px;margin:0 0 16px;background:var(--paper)}}
.eplist h3{{font-size:27px;line-height:1.2;margin:4px 0 8px}}
.eplist h3 a{{color:#3a1530;text-decoration:none}}
.listen h1{{font-weight:600}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site"><div class="wrap">
  <a class="logo" href="/"><img src="/images/kjf-logo-96.png" width="44" height="44" alt="KJF monogram">Kay Joy Flowers</a>
  <nav class="main">
    <a href="/">Home</a>
    <a href="/fearlessly-unfuckwithable.html">Fearlessly Unfuckwithable</a>
    <a href="/genius-insight.html">Energetic Scans</a>
    <a href="/library.html">The Library</a>
    <a href="/blog/">Journal</a>
    <a href="/podcast/" aria-current="page">Podcast</a>
    <a href="/about.html">About</a>
  </nav>
</div></header>
"""


FOOT = """
<footer class="site"><div class="wrap">
  <div>&copy; Kay Joy Flowers. A Living Cosmology of Remembrance.<br><a href="mailto:kay@kayjoyflowers.online">kay@kayjoyflowers.online</a></div>
  <div><a href="/">Home</a> &middot; <a href="/fearlessly-unfuckwithable.html">Fearlessly Unfuckwithable</a> &middot; <a href="/genius-insight.html">Energetic Scans</a> &middot; <a href="/library.html">The Library</a> &middot; <a href="/blog/">Journal</a> &middot; <a href="/podcast/">Podcast</a> &middot; <a href="/about.html">About</a> &middot; <a href="/privacy.html">Privacy</a></div>
</div></footer>
</body>
</html>
"""

AI_NOTE = ("Living Cosmology of Remembrance is created by Kay Joy Flowers and hosted by AI voices, Iris and Jonah. "
           "The ideas and every quotation come from Kay's published writing; the hosts never speak as her.")


def transcript_html(slug):
    rows = []
    for line in open(os.path.join(ROOT, "content", "podcast", f"{slug}_transcript.txt"), encoding="utf-8"):
        m = re.match(r"\[(\d+):([\d.]+)\]\s+(\w+):\s+(.*)", line.strip())
        if m:
            t = int(m.group(1)) * 60 + float(m.group(2))
            rows.append(f'<p><span class="who">{esc(m.group(3))}</span> <span class="muted">{hms(t)}</span><br>{esc(m.group(4))}</p>')
    return "\n".join(rows)


def episode_page(ep):
    slug = ep["slug"]; camp = f"lcr_{slug}"
    url = f"{SITE}/podcast/{slug}/"
    audio = f"/podcast/audio/{slug}.mp3"
    chapters = json.load(open(os.path.join(ROOT, "podcast", slug, "chapters.json")))["chapters"]
    desc = ep["summary"]
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "PodcastEpisode", "@id": f"{url}#episode", "name": ep["title"], "description": desc, "url": url,
         "datePublished": ep["published"][:10], "timeRequired": f"PT{ep['duration'] // 60}M{ep['duration'] % 60}S",
         "episodeNumber": ep["episode"], "inLanguage": "en-NZ", "image": f"{SITE}/podcast/{slug}/cover.jpg",
         "associatedMedia": {"@type": "MediaObject", "contentUrl": f"{SITE}{audio}", "encodingFormat": "audio/mpeg"},
         "partOfSeason": {"@type": "PodcastSeason", "seasonNumber": ep["season"], "name": SERIES[ep["season"]]},
         "partOfSeries": {"@type": "PodcastSeries", "@id": f"{SITE}/podcast/#podcast", "name": TITLE, "url": f"{SITE}/podcast/"},
         "creator": {"@id": f"{SITE}/#kay"}, "isBasedOn": f"{SITE}{ep['essay']}"},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "Podcast", "item": f"{SITE}/podcast/"},
            {"@type": "ListItem", "position": 3, "name": ep["title"], "item": url}]}]}
    out = head(f"{ep['title']} | {TITLE} podcast", desc, url, f"{SITE}/images/og/podcast-{slug}.jpg",
               f"Artwork for {ep['title']}", jsonld)
    ch = "\n".join(f'<li><span class="t">{hms(c["startTime"])}</span><span>{esc(c["title"])}</span></li>' for c in chapters)
    intro = "\n".join(f"<p>{esc(p)}</p>" for p in ep["notes_intro"])
    out += f"""
<main id="main">
<section class="listen"><div class="wrap lgrid">
<img class="art" src="/podcast/{slug}/cover-720.webp" width="720" height="720" alt="Episode artwork: the seven gateways of A Living Cosmology of Remembrance around the podcast title, with Series One and Episode 001.">
<div>
<p class="eyebrow"><a href="/podcast/">{esc(TITLE)}</a> &middot; Series {ep['season']} &middot; Episode {ep['episode']:03d}</p>
<h1>{esc(ep['title'])}</h1>
<p class="byline">Created by <a href="/about.html">Kay Joy Flowers</a> &middot; Series {ep['season']}: {esc(SERIES[ep['season']])} &middot; {hms(ep['duration'])} minutes</p>
<audio class="player" controls preload="none" src="{audio}"></audio>
<p class="elinks"><a href="{audio}" download>Download (MP3)</a> &middot; <a href="#transcript">Transcript</a> &middot; <a href="/podcast/feed.xml">Podcast feed (RSS)</a></p>
</div>
</div></section>
<article class="post"><div class="wrap narrow prose">
<p class="aidisc">{esc(AI_NOTE)}</p>
{intro}
<p><strong>Try this week:</strong> {esc(ep['try_this'])}</p>
<h2>Chapters</h2>
<ul class="chapters">
{ch}
</ul>
<h2>Read and go further</h2>
<p>Read the full essay: <a href="{utm(ep['essay'], camp, 'episode_page_essay')}">{esc(ep['essay_title'])}</a>.</p>
<p>Kay explores sovereignty and personal authority in depth in her book <a href="{utm(ep['book'], camp, 'episode_page_book')}">{esc(ep['book_title'])}</a>.</p>
<p class="cta"><a class="btn primary" href="{utm(ep['book'], camp, 'episode_page_button')}">Discover {esc(ep['book_title'])}</a></p>
<h2 id="transcript">Transcript</h2>
<div class="transcript">
{transcript_html(slug)}
</div>
</div></article>
</main>
"""
    out += FOOT
    os.makedirs(os.path.join(ROOT, "podcast", slug), exist_ok=True)
    open(os.path.join(ROOT, "podcast", slug, "index.html"), "w", encoding="utf-8").write(out)


def index_page():
    url = f"{SITE}/podcast/"
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "PodcastSeries", "@id": f"{url}#podcast", "name": TITLE, "description": SHOW_DESC, "url": url,
         "webFeed": FEED_URL, "image": f"{SITE}/podcast/podcast-cover.jpg", "inLanguage": "en-NZ",
         "creator": {"@type": "Person", "@id": f"{SITE}/#kay", "name": AUTHOR, "url": f"{SITE}/about.html"}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "Podcast", "item": url}]}]}
    out = head(f"{TITLE} | The podcast by Kay Joy Flowers", SHOW_DESC, url, f"{SITE}/images/og/podcast-s01e001.jpg",
               "Living Cosmology of Remembrance podcast artwork", jsonld)
    items = []
    for ep in sorted(EPISODES, key=lambda e: e["published"], reverse=True):
        items.append(f"""<li><p class="eyebrow">Series {ep['season']}: {esc(SERIES[ep['season']])} &middot; Episode {ep['episode']:03d} &middot; {hms(ep['duration'])} minutes</p>
<h3><a href="/podcast/{ep['slug']}/">{esc(ep['title'])}</a></h3>
<p>{esc(ep['summary'])}</p>
<audio class="player" controls preload="none" src="/podcast/audio/{ep['slug']}.mp3"></audio>
<p class="muted"><a href="/podcast/{ep['slug']}/">Show notes and transcript</a></p></li>""")
    latest = sorted(EPISODES, key=lambda e: e["published"], reverse=True)[0]
    latest_card = f"""<div class="epcard">
<p class="k">Latest &middot; Series {latest['season']}: {esc(SERIES[latest['season']])} &middot; Episode {latest['episode']:03d} &middot; {hms(latest['duration'])} min</p>
<h2><a href="/podcast/{latest['slug']}/">{esc(latest['title'])}</a></h2>
<audio class="player" controls preload="none" src="/podcast/audio/{latest['slug']}.mp3"></audio>
<p class="elinks"><a href="/podcast/{latest['slug']}/">Show notes, chapters and transcript</a></p>
</div>"""
    out += f"""
<main id="main">
<section class="listen"><div class="wrap lgrid">
<img class="art" src="/podcast/podcast-cover-720.webp" width="720" height="720" alt="Podcast artwork: the seven gateways of A Living Cosmology of Remembrance, Remembrance, Frequency, Wholeness, Creation, Sovereignty, Expression and Legacy, around the title.">
<div>
<p class="eyebrow">The podcast</p>
<h1>{esc(TITLE)}</h1>
<p class="lede">Conversations that open a doorway into the work of Kay Joy Flowers, one series at a time.</p>
{latest_card}
</div>
</div></section>
<section class="after"><div class="wrap narrow prose">
<p>{esc(SHOW_DESC)}</p>
<p class="aidisc">{esc(AI_NOTE)}</p>
<p class="muted">Follow in any podcast app with the <a href="/podcast/feed.xml">podcast feed (RSS)</a>. Apple Podcasts and Spotify links will appear here once the show is listed.</p>
<h2>All episodes</h2>
<ul class="eplist">
{chr(10).join(items)}
</ul>
</div></section>
</main>
"""
    out += FOOT
    open(os.path.join(ROOT, "podcast", "index.html"), "w", encoding="utf-8").write(out)


def feed():
    guid = uuid.uuid5(uuid.UUID("ead4c236-bf58-58c6-a2c6-a6b28d128cb6"), FEED_URL.split("://")[1])
    items = []
    for ep in sorted(EPISODES, key=lambda e: e["published"], reverse=True):
        slug = ep["slug"]; camp = f"lcr_{slug}"
        when = format_datetime(datetime.fromisoformat(ep["published"]))
        notes = "".join(f"<p>{esc(p)}</p>" for p in ep["notes_intro"])
        notes += f"<p><strong>Try this week:</strong> {esc(ep['try_this'])}</p>"
        notes += f'<p>Read the full essay: <a href="{SITE}{utm(ep["essay"], camp, "shownotes_essay")}">{esc(ep["essay_title"])}</a></p>'
        notes += f'<p>Go deeper: <a href="{SITE}{utm(ep["book"], camp, "shownotes_book")}">{esc(ep["book_title"])}</a> by Kay Joy Flowers</p>'
        notes += f'<p>Show notes, chapters and transcript: <a href="{SITE}/podcast/{slug}/">{SITE}/podcast/{slug}/</a></p>'
        notes += f"<p><em>{esc(AI_NOTE)}</em></p>"
        enclosure = f"{OP3}{SITE.split('://')[1]}/podcast/audio/{slug}.mp3"
        items.append(f"""    <item>
      <title>{esc(ep['title'])}</title>
      <itunes:title>{esc(ep['title'])}</itunes:title>
      <guid isPermaLink="false">kjf-lcr-{slug}</guid>
      <link>{SITE}/podcast/{slug}/</link>
      <pubDate>{when}</pubDate>
      <itunes:season>{ep['season']}</itunes:season>
      <podcast:season name="{esc(SERIES[ep['season']])}">{ep['season']}</podcast:season>
      <itunes:episode>{ep['episode']}</itunes:episode>
      <podcast:episode>{ep['episode']}</podcast:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>{'true' if ep['explicit'] else 'false'}</itunes:explicit>
      <itunes:duration>{ep['duration']}</itunes:duration>
      <itunes:image href="{SITE}/podcast/{slug}/cover.jpg"/>
      <description>{esc(ep['summary'] + ' ' + AI_NOTE)}</description>
      <content:encoded><![CDATA[{notes}]]></content:encoded>
      <enclosure url="{enclosure}" length="{ep['bytes']}" type="audio/mpeg"/>
      <podcast:transcript url="{SITE}/podcast/{slug}/#transcript" type="text/html"/>
      <podcast:chapters url="{SITE}/podcast/{slug}/chapters.json" type="application/json+chapters"/>
    </item>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:podcast="https://podcastindex.org/namespace/1.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{esc(TITLE)}</title>
    <link>{SITE}/podcast/</link>
    <atom:link href="{FEED_URL}" rel="self" type="application/rss+xml"/>
    <language>en-nz</language>
    <copyright>© {datetime.now(timezone.utc).year} {AUTHOR}</copyright>
    <description>{esc(SHOW_DESC)}</description>
    <itunes:summary>{esc(SHOW_DESC)}</itunes:summary>
    <itunes:author>{AUTHOR}</itunes:author>
    <podcast:person group="writing" role="author" href="{SITE}/about.html">{AUTHOR}</podcast:person>
    <itunes:owner><itunes:name>{AUTHOR}</itunes:name><itunes:email>{EMAIL}</itunes:email></itunes:owner>
    <itunes:image href="{SITE}/podcast/podcast-cover.jpg"/>
    <image><url>{SITE}/podcast/podcast-cover.jpg</url><title>{esc(TITLE)}</title><link>{SITE}/podcast/</link></image>
    <itunes:category text="Religion &amp; Spirituality"><itunes:category text="Spirituality"/></itunes:category>
    <itunes:category text="Education"><itunes:category text="Self-Improvement"/></itunes:category>
    <itunes:explicit>true</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <podcast:locked owner="{EMAIL}">yes</podcast:locked>
    <podcast:guid>{guid}</podcast:guid>
    <podcast:medium>podcast</podcast:medium>
{chr(10).join(items)}
  </channel>
</rss>
"""
    open(os.path.join(ROOT, "podcast", "feed.xml"), "w", encoding="utf-8").write(xml)


if __name__ == "__main__":
    for ep in EPISODES:
        episode_page(ep)
    index_page()
    feed()
    print("podcast pages and feed written")
