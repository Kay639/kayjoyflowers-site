# Executive summary: SEO and AEO work on kayjoyflowers.online

**Status:** **live and verified** on 18 November 2026 (NZ) · deployed commit `eadf317` on `main` (fast-forward from `116b245`, no force-push)

## Outcome (measured on the live site, before and after)
| | Before | After |
|---|---|---|
| Audit score (49 checks, same script both times) | **68 / 100 (D)** | **99 / 100 (A)** |
| Critical / high findings | 0 / 9 | 0 / 0 |
| Lighthouse accessibility | 94–100 | 100 on every page |
| Lighthouse best practices | 96 | 100 on every page |
| Library page LCP (mobile, simulated) | 3.50 s | 1.76 s |
| About page weight | 1,043 KB | 123 KB |

Lighthouse figures are the median of 3 mobile runs on the live site. No rankings, traffic or AI citations are claimed: those can only be measured once Google Search Console has collected data (allow 2–6 weeks).

## Deployment checks
- The GitHub Pages build (run #20) and the new SEO/AEO CI checks on `main` both succeeded.
- All 27 published files on kayjoyflowers.online are byte-identical to a local build of `main`.
- Reports, docs, tools and config are not public (404). Missing pages show the branded 404 page.
- robots.txt allows Google, Bing and the AI search crawlers (ChatGPT search, Perplexity, Claude search). It blocks the AI training crawlers (GPTBot, ClaudeBot, Google-Extended), as Kay asked.
- Checkout links are unchanged. The Stripe links return 200 from the live pages.

## What was delivered
1. **Baseline audit:** `01-baseline-audit.html`.
2. **Website improvements:**
   - Kay's supplied patch, verified rather than redone.
   - Search-length titles and descriptions, per-page share images and a favicon.
   - Corrected and extended structured data.
   - Image and speed fixes, accessibility fixes, the Library image bug, consistent footers and a 404 page.
   - The robots.txt crawler policy.
3. **Post-deploy audit and before/after:** `02-after-audit.html`.
4. **Publishing standard:** `docs/seo-aeo/`.
5. **Automated validation:** `.github/workflows/seo-checks.yml` runs on every push, plus a weekly live audit.
6. **Deployment verification:** above.

## Unchanged by design
Prices, checkout links, products, visible page copy, imagery and design.

## Still needs Kay
- **Click the two Beacons buttons once:** "Get the Bundle — US$77" and "Buy the book — US$33". Beacons blocks automated checks.
- **Approve or edit** the Fearlessly Unfuckwithable FAQ draft (`drafts/`).
- **Library:** one or two lines per collection, in Kay's words. This is the only remaining audit gap.
- **Set up Google Search Console** (free) and submit `https://kayjoyflowers.online/sitemap.xml`.
- **Confirm "Enforce HTTPS"** in GitHub → Settings → Pages.

**Rollback, if ever needed:** reset `main` to `116b245` (or revert the range). GitHub Pages redeploys automatically.
