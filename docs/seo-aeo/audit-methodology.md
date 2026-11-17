# Audit methodology

The scores in `reports/` come from `tools/seo_audit.py`. Run it on the same site and you get the same score. This page explains how it works so a score can be checked, not taken on trust.

## What it crawls
- Starts at `/` and every URL in `sitemap.xml`, then follows every internal link.
- Also fetches the private pages (`/scan-intake.html`, `/companion/`, `/companion-sovereign/`) to confirm they are noindexed and kept out of the sitemap.
- Fetches `robots.txt`, `sitemap.xml`, `llms.txt` and a made-up URL (to test that missing pages return a real 404).
- `--root .` serves the repository the way GitHub Pages does (`/about` → `about.html`, real 404s, `reports/`, `docs/` and `tools/` hidden). Before any changes were made, the local and live results were identical: 68/100, with the same failed checks.

## Checks, categories and weights
There are 49 checks, defined in the `CHECKS` table at the top of the script. Each has a category, a severity, the principle behind it and the fix.

| Severity | Weight | Meaning |
|---|---|---|
| critical | 5 | Stops a page being found, loaded or bought |
| high | 3 | Directly harms indexing, rich results, accessibility or the main image load |
| medium | 2 | Weakens how the page is understood, shared or used |
| low | 1 | Polish and best practice |

Categories: Technical SEO, Metadata & Social, Structured Data, AEO & Content, Accessibility, Performance, Conversion.

## Scoring
- A check runs once per page it applies to (site-wide checks run once).
- **Category score** = weight of passed runs ÷ weight of all runs × 100, rounded.
- **Overall** = the same sum across all categories.
- Grades: A ≥ 90, B 80–89, C 70–79, D 60–69, F < 60.
- **Unverified** checks are left out of the score. These are checks the tool can't complete, such as Beacons checkout pages that block automated visitors. They are listed separately and never counted as passes.

## What the score is not
- Not a ranking prediction and not a Google score. It measures whether known good practices are in place.
- Lighthouse results (`tools/lighthouse_runs.mjs`: mobile, simulated throttling, median of 3 runs) are reported separately as measured performance and accessibility. Findings from screenshots and manual review are listed with their evidence but don't change the score, so the score stays repeatable.
- No traffic, ranking or AI-citation figures are claimed anywhere unless they come from a real source, such as Google Search Console.

## Other automated checks
- `tools/jsonld-check/check.mjs`: type-checks every JSON-LD block against the schema.org vocabulary (Google's `schema-dts` definitions plus the TypeScript compiler). It catches unknown properties, misspelt types and wrong value types.
- `tools/build_sitemap.py --check`: confirms the sitemap lists exactly the indexable pages.

## Running a full audit (about 20 minutes)
```bash
python3 tools/seo_audit.py --base https://kayjoyflowers.online --json audit.json
```
```bash
mkdir -p /tmp/lh && cd /tmp/lh && npm i lighthouse@12 && node /path/to/repo/tools/lighthouse_runs.mjs --runs 3 --out lh.json
```
```bash
python3 tools/build_report.py baseline --data reports/NEW-FOLDER/data --out reports/NEW-FOLDER/01-audit.html
```
Then compare the new report against the previous one. Re-run after any big content change, and at least monthly. The weekly CI job runs the live audit automatically.
