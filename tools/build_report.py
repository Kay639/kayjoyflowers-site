#!/usr/bin/env python3
"""Build the self-contained HTML audit reports from tools/seo_audit.py output.

Baseline:
  python3 tools/build_report.py baseline --data reports/2026-11-seo-aeo/data \
      --shots /path/to/screenshots --out reports/2026-11-seo-aeo/01-baseline-audit.html
After (before/after comparison):
  python3 tools/build_report.py after --data reports/2026-11-seo-aeo/data \
      --shots-before DIR --shots-after DIR --out reports/2026-11-seo-aeo/02-after-audit.html

Data files read from --data: baseline-audit.json, baseline-lighthouse.json, manual-findings.json,
patch-verification-audit.json and, for 'after': after-audit.json, after-lighthouse.json,
after-status.json (status of each manual finding, tests run, deployment state).
Add --fragment to write the page without <html>/<head>/<body> (for hosts that wrap it).
"""
import argparse
import base64
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from seo_audit import CATEGORIES, SEVERITY_ORDER, grade  # noqa: E402

E = html.escape

CSS = """
:root{
  /* layout: one editorial column, score strip up top, findings as a severity-striped list */
  --bg:#F4F2F4; --paper:#FFFFFF; --ink:#1F1A22; --muted:#5F5866; --line:#DCD6DE;
  --accent:#7A1F3D; --accent-soft:#F3E3E9; --sage:#4E6656; --sage-soft:#E3ECE5;
  --crit:#A3122F; --high:#B4521A; --med:#8A6D00; --low:#4E6656; --track:#E7E2E8;
  --display:"Bodoni Moda", Georgia, "Times New Roman", serif;
  --body:"Karla", "Helvetica Neue", Arial, sans-serif;
  --mono:ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  color-scheme:light;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#17141A; --paper:#211D25; --ink:#EEEAF0; --muted:#ABA3B1; --line:#3A3440;
  --accent:#E58AA8; --accent-soft:#3B2230; --sage:#9EC2A9; --sage-soft:#22302A;
  --crit:#FF7A8E; --high:#F0A070; --med:#E2C25A; --low:#9EC2A9; --track:#2E2934; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#17141A; --paper:#211D25; --ink:#EEEAF0; --muted:#ABA3B1; --line:#3A3440;
  --accent:#E58AA8; --accent-soft:#3B2230; --sage:#9EC2A9; --sage-soft:#22302A;
  --crit:#FF7A8E; --high:#F0A070; --med:#E2C25A; --low:#9EC2A9; --track:#2E2934; color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.65 var(--body)}
.wrap{max-width:1000px;margin:0 auto;padding-block:40px 80px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
h1,h2,h3{font-family:var(--display);font-weight:500;line-height:1.15;text-wrap:balance;margin:0}
h1{font-size:clamp(34px,5vw,52px)} h2{font-size:clamp(26px,3.4vw,34px);margin-top:56px} h3{font-size:20px}
p{margin:0 0 12px} a{color:var(--accent)}
.eyebrow{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:var(--accent);font-weight:600;margin:0 0 10px}
.lede{font-family:var(--display);font-style:italic;font-size:21px;color:var(--muted);max-width:680px;margin-top:14px}
.muted{color:var(--muted)} .small{font-size:14.5px}
.meta{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:20px;font-size:14.5px;color:var(--muted)}
.meta b{color:var(--ink);font-weight:600}
.panel{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:22px}
.overall{display:grid;grid-template-columns:auto 1fr;gap:26px;align-items:center;margin-top:28px}
.big{font-family:var(--display);font-size:76px;line-height:1;font-variant-numeric:tabular-nums}
.big small{font-size:22px;color:var(--muted)}
.gradechip{display:inline-block;font-weight:600;font-size:14px;border-radius:999px;padding:2px 10px;background:var(--accent-soft);color:var(--accent);margin-left:8px;vertical-align:middle}
.bars{display:grid;gap:10px;margin-top:6px}
.bar{display:grid;grid-template-columns:150px minmax(0,1fr) 92px;gap:12px;align-items:center;font-size:15px}
.track{height:10px;background:var(--track);border-radius:99px;position:relative;overflow:hidden}
.fill{position:absolute;inset:0 auto 0 0;background:var(--accent);border-radius:99px}
.fill.before{background:var(--muted);opacity:.45}
.num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
@media (max-width:640px){.overall{grid-template-columns:1fr}.bar{grid-template-columns:1fr 70px}.bar .track{grid-column:1/-1;order:3}}
.tablewrap{overflow-x:auto;margin-top:14px}
table{border-collapse:collapse;width:100%;font-size:14.5px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.05em}
td.n{text-align:right}
.findings{display:grid;gap:12px;margin-top:16px}
.f{background:var(--paper);border:1px solid var(--line);border-left:5px solid var(--sev);border-radius:10px;padding:16px 18px}
.f.critical{--sev:var(--crit)} .f.high{--sev:var(--high)} .f.medium{--sev:var(--med)} .f.low{--sev:var(--low)}
.f header{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:baseline;justify-content:space-between}
.f h3{font-family:var(--body);font-weight:600;font-size:17px}
.pill{font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;border-radius:999px;padding:2px 9px;border:1px solid var(--sev,var(--line));color:var(--sev,var(--muted));white-space:nowrap}
.pill.ok{--sev:var(--sage)} .pill.open{--sev:var(--high)} .pill.acc{--sev:var(--muted)}
.f dl{display:grid;grid-template-columns:96px minmax(0,1fr);gap:4px 12px;margin:10px 0 0;font-size:15px}
.f dt{color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.05em;padding-top:2px}
.f dd{margin:0;min-width:0;overflow-wrap:anywhere}
@media (max-width:560px){.f dl{grid-template-columns:1fr}.f dt{padding-top:6px}}
code{font-family:var(--mono);font-size:.88em;background:var(--accent-soft);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere}
.shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;margin-top:16px}
.shots figure{margin:0}.shots img{width:100%;border:1px solid var(--line);border-radius:8px;display:block}
.shots figcaption{font-size:13.5px;color:var(--muted);margin-top:6px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.callout{background:var(--sage-soft);border-radius:12px;padding:16px 18px;margin-top:16px}
ul.tight{margin:8px 0 0;padding-left:20px} ul.tight li{margin-bottom:4px}
.up{color:var(--sage);font-weight:600} .down{color:var(--crit);font-weight:600}
footer{margin-top:64px;font-size:14px;color:var(--muted);border-top:1px solid var(--line);padding-top:18px}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500;1,600&family=Inter:wght@400;500;600&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap">')


def load(d, name, default=None):
    p = os.path.join(d, name)
    if not os.path.exists(p):
        return default
    with open(p) as fh:
        return json.load(fh)


def img64(path):
    with open(path, "rb") as fh:
        return "data:image/jpeg;base64," + base64.b64encode(fh.read()).decode()


def page(title, body, fragment):
    head = f'<title>{E(title)}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n{FONTS}\n<style>{CSS}</style>\n'
    if fragment:
        return head + body
    return ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<meta name="robots" content="noindex, nofollow">\n' + head + '</head>\n<body>\n' + body + '\n</body>\n</html>\n')


def grouped_failures(audit):
    """One finding per failed check, listing every affected URL."""
    out = {}
    for r in audit["results"]:
        if r["passed"] is False:
            g = out.setdefault(r["check"], {"check": r["check"], "severity": r["severity"], "category": r["category"],
                                            "title": r["title"], "items": []})
            g["items"].append((r["url"], r["detail"]))
    return sorted(out.values(), key=lambda g: (SEVERITY_ORDER.index(g["severity"]), g["category"], g["check"]))


def finding_html(sev, title, category, urls_html, evidence, principle, fix, status=None):
    st = ""
    if status:
        cls = {"resolved": "ok", "open": "open", "accepted": "acc", "needs-kay": "open", "verified": "ok"}.get(status[0], "acc")
        st = f'<span class="pill {cls}">{E(status[0].replace("-", " "))}</span>'
    rows = f"<dt>Where</dt><dd>{urls_html}</dd>"
    if evidence:
        rows += f"<dt>Evidence</dt><dd>{evidence}</dd>"
    rows += f"<dt>Why</dt><dd>{E(principle)}</dd><dt>Fix</dt><dd>{E(fix)}</dd>"
    if status and status[1]:
        rows += f"<dt>Result</dt><dd>{E(status[1])}</dd>"
    return (f'<article class="f {sev}"><header><h3>{E(title)}</h3><span>'
            f'<span class="pill">{E(sev)}</span> <span class="pill acc">{E(category)}</span> {st}</span></header>'
            f'<dl>{rows}</dl></article>')


def score_bars(cats, before=None):
    out = []
    for c in CATEGORIES:
        v = cats.get(c)
        if not v or v.get("score") is None:
            continue
        s = v["score"]
        b = before.get(c, {}).get("score") if before else None
        fills = (f'<span class="fill before" style="width:{b}%"></span>' if b is not None else "") + \
                f'<span class="fill" style="width:{s}%;{"opacity:.9" if b is not None else ""}"></span>'
        label = f"{b} → {s}" if b is not None else f"{s}"
        out.append(f'<div class="bar"><span>{E(c)}</span><span class="track" role="img" aria-label="{E(c)} {label} out of 100">{fills}</span>'
                   f'<span class="num"><b>{label}</b> {grade(s)}</span></div>')
    return '<div class="bars">' + "".join(out) + "</div>"


def lh_table(lh, before=None):
    if not lh:
        return "<p class='muted'>Not measured.</p>"
    head = "<tr><th>Page</th><th>Performance</th><th>Accessibility</th><th>Best practices</th><th>SEO</th><th>LCP</th><th>CLS</th><th>Page weight</th></tr>"
    rows = []
    for p, m in lh["pages"].items():
        b = (before or {}).get("pages", {}).get(p)

        def cell(k, fmt, better="up"):
            v = m[k]
            txt = fmt(v)
            if b is not None:
                bv = b[k]
                if fmt(bv) != txt:
                    good = (v > bv) if better == "up" else (v < bv)
                    txt = f"{fmt(bv)} → <span class='{'up' if good else 'down'}'>{txt}</span>"
            return f"<td class='n'>{txt}</td>"
        rows.append(f"<tr><td>{E(p)}</td>" + cell("performance", str) + cell("accessibility", str) + cell("bestPractices", str)
                    + cell("seo", str) + cell("lcp", lambda v: f"{v/1000:.2f} s", "down") + cell("cls", lambda v: f"{v:.3f}", "down")
                    + cell("bytes", lambda v: f"{round(v/1024)} KB", "down") + "</tr>")
    return f'<div class="tablewrap"><table>{head}{"".join(rows)}</table></div>'


def urls_list(items):
    if len(items) == 1 and not items[0][1]:
        return f"<code>{E(items[0][0])}</code>"
    return "<ul class='tight'>" + "".join(f"<li><code>{E(u)}</code>{(' ' + E(d)) if d else ''}</li>" for u, d in items) + "</ul>"


METHOD = """
<h2 id="method">How the scores work</h2>
<p>Every score comes from <code>tools/seo_audit.py</code>, which you can run again at any time and get the same result for the same site. It crawls the site from the home page and the sitemap, follows every internal link, and runs {n} defined checks. Each check belongs to one category and has a fixed severity:</p>
<div class="tablewrap"><table><tr><th>Severity</th><th>Weight</th><th>Meaning</th></tr>
<tr><td>Critical</td><td class="n">5</td><td>Stops a page being found, loaded or bought</td></tr>
<tr><td>High</td><td class="n">3</td><td>Directly harms indexing, rich results, accessibility or the main image load</td></tr>
<tr><td>Medium</td><td class="n">2</td><td>Weakens how the page is understood, shared or used</td></tr>
<tr><td>Low</td><td class="n">1</td><td>Polish and best practice</td></tr></table></div>
<p style="margin-top:14px"><b>Category score</b> = weight of passed checks ÷ weight of all checks run, × 100. A check runs once per page it applies to, so a problem on six pages counts six times. <b>Overall</b> is the same sum across all categories. Grades: A 90+, B 80–89, C 70–79, D 60–69, F below 60.</p>
<p>Checks the audit cannot complete (for example checkout pages behind bot protection) are listed as <i>unverified</i> and left out of the score rather than counted as passes. Lighthouse figures are separate, measured evidence: Lighthouse {lhv}, mobile profile with simulated throttling, median of {runs} runs per page. Findings from Lighthouse, screenshots and manual review are listed with their evidence but are not part of the score, so the score stays repeatable.</p>
<p class="small muted">Reproduce: <code>python3 tools/seo_audit.py --base https://kayjoyflowers.online</code> · local copy: <code>python3 tools/seo_audit.py --root .</code> · Lighthouse: <code>node tools/lighthouse_runs.mjs --runs 3</code></p>
"""


def baseline(args):
    d = args.data
    a = load(d, "baseline-audit.json")
    lh = load(d, "baseline-lighthouse.json")
    manual = load(d, "manual-findings.json", [])
    patch = load(d, "patch-verification-audit.json")
    pages_ = a["pages"]
    idx = [p for p, v in pages_.items() if v["indexable"]]
    fails = grouped_failures(a)
    counts = {s: 0 for s in SEVERITY_ORDER}
    for g in fails:
        counts[g["severity"]] += 1
    for m in manual:
        counts[m["severity"]] = counts.get(m["severity"], 0) + 1

    body = ['<div class="wrap">',
            '<p class="eyebrow">Phase 1 · Baseline audit · 17–18 November 2026</p>',
            '<h1>kayjoyflowers.online, before any changes</h1>',
            '<p class="lede">What search engines and AI answer engines found on the live site, what it costs, and how to fix each problem.</p>',
            f'<div class="meta"><span><b>Audited:</b> live site, HTTPS</span><span><b>Source:</b> <code>main</code> @ 116b245 (live HTML verified byte-for-byte identical)</span>'
            f'<span><b>Public pages:</b> {len(idx)}</span><span><b>Private pages checked:</b> 3</span><span><b>Checks run:</b> {len(a["results"])}</span></div>',
            '<div class="panel overall"><div><div class="big">' + str(a["overall"]) + '<small>/100</small></div>'
            f'<div class="muted small">Overall <span class="gradechip">{grade(a["overall"])}</span></div></div>' + score_bars(a["categories"]) + '</div>',
            '<h2>Summary</h2>',
            '<p>The site is fast, readable on phones and honestly written. What it lacks is the plumbing machines rely on: no robots.txt, no sitemap, no canonical URLs, no social share tags and no structured data. As a result, Google and AI answer engines have to guess who Kay is, what the books cost and which URL counts. Nothing is broken for visitors except one visual bug on the Library page.</p>',
            f'<p>Findings: <b>{counts["critical"]}</b> critical, <b>{counts["high"]}</b> high, <b>{counts["medium"]}</b> medium and <b>{counts["low"]}</b> low (failed checks grouped by type, plus {len(manual)} findings from Lighthouse, screenshots and manual review).</p>']
    if patch:
        body.append('<div class="callout"><b>The supplied patch is already applied and verified on branch <code>seo-aeo-fixes</code>.</b> '
                    f'Re-running the same audit on that branch gives {patch["overall"]}/100 ({grade(patch["overall"])}), up from {a["overall"]}. '
                    'It fixes robots.txt, the sitemap, canonicals, Open Graph, author attribution and structured data. The items it doesn\'t cover are listed as still open in the after-report.'
                    f'{score_bars(patch["categories"], a["categories"])}</div>')
    body.append('<h2>Measured performance (Lighthouse)</h2>')
    body.append('<p>Speed is already good: performance 90–99 on every page, with no layout shift. Two problems stand out. The Library page\'s main image is lazy-loaded, which slows its largest paint to 3.5 s. The About page portrait weighs 515 KB, giving that page a total weight of 1 MB.</p>')
    body.append(lh_table(lh))
    body.append('<h2>Findings, most serious first</h2>')
    body.append('<p class="muted">Each finding gives the problem, the principle behind it and the fix. Coloured edges mark severity.</p>')
    for sev in SEVERITY_ORDER:
        group = [g for g in fails if g["severity"] == sev]
        man = [m for m in manual if m["severity"] == sev]
        if not group and not man:
            continue
        body.append(f'<h3 style="margin-top:30px;font-family:var(--display);font-size:24px">{sev.capitalize()}</h3><div class="findings">')
        for g in group:
            c = a["checks"][g["check"]]
            body.append(finding_html(sev, g["title"], g["category"], urls_list(g["items"]), "", c["principle"], c["fix"]))
        for m in man:
            body.append(finding_html(sev, m["title"], m["category"], ", ".join(f"<code>{E(u)}</code>" for u in m["urls"]),
                                     E(m["evidence"]), m["principle"], m["fix"]))
        body.append("</div>")
    unv = [r for r in a["results"] if r["passed"] is None]
    if unv:
        body.append('<h3 style="margin-top:30px;font-family:var(--display);font-size:24px">Could not be verified automatically</h3><ul class="tight">')
        body += [f"<li>{E(r['title'])}: <code>{E(r['detail'])}</code></li>" for r in unv]
        body.append("</ul>")
    if args.shots and os.path.isdir(args.shots):
        body.append('<h2>How it looks today</h2><p>Live screenshots at phone width (390 px) and desktop width (1280 px). No page scrolls sideways on a phone and no tap target is too small. The Library card images (third picture) don\'t reach the right edge of their cards.</p><div class="shots">')
        for f, cap in [("mobile-home.jpg", "Home, phone"), ("mobile-fearlessly-unfuckwithable.jpg", "Fearlessly Unfuckwithable, phone"),
                       ("mobile-library.jpg", "Library, phone: card image gap"), ("mobile-genius-insight.jpg", "Energetic Scans, phone"),
                       ("desktop-home.jpg", "Home, desktop")]:
            p = os.path.join(args.shots, f)
            if os.path.exists(p):
                body.append(f'<figure><img src="{img64(p)}" alt="Screenshot: {E(cap)}" loading="lazy"><figcaption>{E(cap)}</figcaption></figure>')
        body.append("</div>")
    body.append('<h2>Pages found</h2><div class="tablewrap"><table><tr><th>URL</th><th>Status</th><th>Indexable</th><th>Words</th><th>Title</th></tr>')
    for p, v in pages_.items():
        body.append(f"<tr><td><code>{E(p)}</code></td><td class='n'>{v['status']}</td><td>{'yes' if v['indexable'] else 'no'}</td><td class='n'>{v['words']}</td><td>{E(v['title'] or '')}</td></tr>")
    body.append("</table></div>")
    body.append(METHOD.format(n=len(a["checks"]), lhv=E(lh.get("lighthouse") or "?"), runs=lh.get("runs", 3)))
    body.append('<h2>About the reference method</h2><p>This follows the loop in Mika Reyes\'s <i>How to audit your website for SEO and AEO with AI</i>: a teaching-first audit (problem → principle → fix), implementation, a re-audit with the same method, verification on the live site, and a publishing standard so new pages start clean. One change from the article: its letter grades were "directional". Here every score comes from a script, so it can be repeated and checked.</p>')
    body.append('<footer>Generated by <code>tools/build_report.py</code> from <code>reports/2026-11-seo-aeo/data/</code>. No rankings, traffic or AI-citation figures are reported, because none were measured.</footer></div>')
    return page("SEO/AEO Baseline Audit", "\n".join(body), args.fragment)


def after(args):
    d = args.data
    a0 = load(d, "baseline-audit.json")
    ap = load(d, "patch-verification-audit.json")
    a1 = load(d, "after-audit.json")
    lh0 = load(d, "baseline-lighthouse.json")   # live site before; after-lighthouse.json is the live site after
    lh1 = load(d, "after-lighthouse.json")
    manual = load(d, "manual-findings.json", [])
    st = load(d, "after-status.json", {})
    statuses = st.get("manual", {})

    f0 = {g["check"]: g for g in grouped_failures(a0)}
    f1 = {g["check"]: g for g in grouped_failures(a1)}
    resolved = [g for k, g in f0.items() if k not in f1]
    partly = [(g, f1[k]) for k, g in f0.items() if k in f1]
    new = [g for k, g in f1.items() if k not in f0]

    body = ['<div class="wrap">',
            '<p class="eyebrow">Phases 4–6 · Re-audit, deployment and before/after · ' + E(st.get("date", "")) + '</p>',
            '<h1>kayjoyflowers.online, after the SEO and AEO work</h1>',
            '<p class="lede">Same audit, same rules, run again on the deployed site. This page covers what improved, what is still open, and what can\'t be measured yet.</p>',
            f'<div class="meta"><span><b>Branch:</b> <code>{E(st.get("branch", ""))}</code></span><span><b>Commit:</b> <code>{E(st.get("commit", "see git log"))}</code></span>'
            f'<span><b>Deployment:</b> {E(st.get("deployment", ""))}</span></div>',
            '<div class="panel overall"><div><div class="big">' + str(a1["overall"]) + '<small>/100</small></div>'
            f'<div class="muted small">was {a0["overall"]} <span class="gradechip">{grade(a0["overall"])} → {grade(a1["overall"])}</span></div></div>'
            + score_bars(a1["categories"], a0["categories"]) + '</div>',
            '<h2>Scores at each stage</h2><div class="tablewrap"><table><tr><th>Category</th><th>Live site before</th><th>After supplied patch</th><th>Live site after</th></tr>']
    for c in CATEGORIES:
        s0, sp, s1 = (x["categories"][c]["score"] for x in (a0, ap, a1))
        body.append(f"<tr><td>{E(c)}</td><td class='n'>{s0} {grade(s0)}</td><td class='n'>{sp} {grade(sp)}</td><td class='n'><b>{s1} {grade(s1)}</b></td></tr>")
    body.append(f"<tr><td><b>Overall</b></td><td class='n'>{a0['overall']}</td><td class='n'>{ap['overall']}</td><td class='n'><b>{a1['overall']}</b></td></tr></table></div>")
    body.append(f'<p class="small muted" style="margin-top:10px">{E(st.get("score_note", ""))}</p>')

    body.append('<h2>What is verified, what is expected, what can\'t be measured yet</h2><div class="tablewrap"><table><tr><th>Type</th><th>Items</th></tr>')
    for k, label in [("verified", "Verified (measured in this work)"), ("expected", "Expected benefit (not measurable yet)"), ("unmeasurable", "Can't be measured yet")]:
        body.append(f"<tr><td>{E(label)}</td><td><ul class='tight'>" + "".join(f"<li>{E(x)}</li>" for x in st.get(k, [])) + "</ul></td></tr>")
    body.append("</table></div>")

    body.append('<h2>Performance and accessibility (Lighthouse)</h2>')
    body.append(f'<p>{E(st.get("lighthouse_note", ""))}</p>')
    body.append(lh_table(lh1, lh0))

    body.append('<h2>Structured data, page by page</h2><div class="tablewrap"><table><tr><th>Page</th><th>Before</th><th>After</th></tr>')
    for p, types in st.get("schema", {}).items():
        body.append(f"<tr><td><code>{E(p)}</code></td><td>none</td><td>{E(types)}</td></tr>")
    body.append("</table></div>")

    body.append(f'<h2>Resolved ({len(resolved)} failed-check types, plus manual findings)</h2><div class="findings">')
    for g in resolved:
        c = a0["checks"][g["check"]]
        body.append(finding_html(g["severity"], g["title"], g["category"], urls_list(g["items"]), "", c["principle"], c["fix"],
                                 ("resolved", "Passes on every page now.")))
    for m in manual:
        s = statuses.get(m["id"])
        if s and s[0] in ("resolved", "verified"):
            body.append(finding_html(m["severity"], m["title"], m["category"], ", ".join(f"<code>{E(u)}</code>" for u in m["urls"]),
                                     E(m["evidence"]), m["principle"], m["fix"], tuple(s)))
    body.append("</div>")

    body.append('<h2>Still open or accepted</h2><div class="findings">')
    for g0, g1 in partly:
        c = a0["checks"][g0["check"]]
        body.append(finding_html(g1["severity"], g1["title"], g1["category"], urls_list(g1["items"]), "", c["principle"], c["fix"],
                                 tuple(st.get("open_checks", {}).get(g0["check"], ["open", f"{len(g0['items'])} → {len(g1['items'])} affected"]))))
    for g in new:
        c = a1["checks"][g["check"]]
        body.append(finding_html(g["severity"], g["title"], g["category"], urls_list(g["items"]), "", c["principle"], c["fix"],
                                 tuple(st.get("open_checks", {}).get(g["check"], ["open", "Found by the re-audit."]))))
    for m in manual:
        s = statuses.get(m["id"])
        if not s or s[0] not in ("resolved", "verified"):
            body.append(finding_html(m["severity"], m["title"], m["category"], ", ".join(f"<code>{E(u)}</code>" for u in m["urls"]),
                                     E(m["evidence"]), m["principle"], m["fix"], tuple(s or ("open", ""))))
    body.append("</div>")

    body.append('<h2>Changes made</h2>')
    for title, items in st.get("changes", {}).items():
        body.append(f"<h3 style='margin-top:20px'>{E(title)}</h3><ul class='tight'>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>")

    if args.shots_before and args.shots_after:
        body.append('<h2>Before and after</h2><div class="shots" style="grid-template-columns:1fr">')
        for f, cap in [("mobile-library.jpg", "Library, phone: card images now fill their cards, collection titles are H2s"),
                       ("mobile-home.jpg", "Home, phone: no visible change intended (skip link appears only on keyboard focus)"),
                       ("desktop-fearlessly-unfuckwithable.jpg", "Fearlessly Unfuckwithable, desktop: no visible change intended")]:
            b, n = os.path.join(args.shots_before, f), os.path.join(args.shots_after, f)
            if os.path.exists(b) and os.path.exists(n):
                body.append(f'<figure><div class="pair"><img src="{img64(b)}" alt="Before: {E(cap)}" loading="lazy"><img src="{img64(n)}" alt="After: {E(cap)}" loading="lazy"></div><figcaption>Before (left) and after (right). {E(cap)}</figcaption></figure>')
        og = st.get("og_images", [])
        body.append("</div>")
        if og:
            body.append('<h3 style="margin-top:28px">New share images (1200×630)</h3><div class="shots">')
            for path, cap in og:
                if os.path.exists(path):
                    body.append(f'<figure><img src="{img64(path)}" alt="Share image: {E(cap)}" loading="lazy"><figcaption>{E(cap)}</figcaption></figure>')
            body.append("</div>")

    body.append('<h2>Tests run</h2><div class="tablewrap"><table><tr><th>Test</th><th>Result</th></tr>')
    for t, r in st.get("tests", []):
        body.append(f"<tr><td>{E(t)}</td><td>{E(r)}</td></tr>")
    body.append("</table></div>")

    body.append('<h2>Waiting on Kay or outside services</h2><ul class="tight">' + "".join(f"<li>{x}</li>" for x in st.get("external", [])) + "</ul>")
    body.append(f'<h2>Deployment</h2><p>{st.get("deployment_detail", "")}</p>')
    body.append(METHOD.format(n=len(a1["checks"]), lhv=E((lh1 or {}).get("lighthouse") or "?"), runs=(lh1 or {}).get("runs", 3)))
    body.append('<footer>Generated by <code>tools/build_report.py</code> from <code>reports/2026-11-seo-aeo/data/</code>. No rankings, traffic or AI-citation changes are claimed, because none have been measured.</footer></div>')
    return page("SEO/AEO Before and After", "\n".join(body), args.fragment)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["baseline", "after"])
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shots")
    ap.add_argument("--shots-before")
    ap.add_argument("--shots-after")
    ap.add_argument("--fragment", action="store_true")
    args = ap.parse_args()
    html_ = baseline(args) if args.mode == "baseline" else after(args)
    with open(args.out, "w") as fh:
        fh.write(html_)
    print(f"Wrote {args.out} ({len(html_)//1024} KB)")


if __name__ == "__main__":
    main()
