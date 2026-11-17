# SEO and AEO system for kayjoyflowers.online

| Document | Use it when |
|---|---|
| [PUBLISHING-STANDARD.md](PUBLISHING-STANDARD.md) | Creating or changing any page |
| [templates/page-head.html](templates/page-head.html) | Starting a new page (complete head, nav, skip link, footer) |
| [templates/structured-data.md](templates/structured-data.md) | Adding a book, product, service, FAQ or article |
| [audit-methodology.md](audit-methodology.md) | Reading or reproducing a score |
| [content-opportunities.md](content-opportunities.md) | Planning what to write next |

Audit reports live in `reports/` (newest first: `reports/2026-11-seo-aeo/`). Reports, docs and tools are kept out of the published website by `_config.yml`.

## Automated checks

They run on every push and pull request (`.github/workflows/seo-checks.yml`), and against the live site every Monday:

| Check | Command (from the repository root) | Fails when |
|---|---|---|
| SEO/AEO audit | `python3 tools/seo_audit.py --root . --offline --fail-on high` | any critical or high check fails |
| Sitemap is current | `python3 tools/build_sitemap.py --check` | an indexable page is missing, or a removed or noindex page is listed |
| Structured data | `cd tools/jsonld-check && npm ci && node check.mjs` | JSON-LD doesn't match schema.org |
| Live audit (weekly) | `python3 tools/seo_audit.py --base https://kayjoyflowers.online --fail-on critical` | a critical problem appears on the live site |

Only Python 3 and Node are needed, and no paid services. Lighthouse (`tools/lighthouse_runs.mjs`) and the image generator (`tools/make_images.mjs`) are run by hand when needed. Each file has setup notes at the top.

## Typical workflow for a new page
1. Copy `templates/page-head.html` to the new page and fill in every placeholder.
2. Add a share image entry to `tools/og-images.json` and run `node tools/make_images.mjs`.
3. Link the page from the nav, the footer or a related page.
4. Run the three checks above. Fix anything they report.
5. Commit, run `python3 tools/build_sitemap.py`, and commit `sitemap.xml`.
6. If it's a major page, add a line to `llms.txt`.
