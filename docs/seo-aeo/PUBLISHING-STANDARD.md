# Kay Joy Flowers: SEO and AEO publishing standard

Use this for every new or changed page on kayjoyflowers.online: product pages, landing pages, articles and guides. It keeps each new page as findable and quotable as the existing ones.

The automated checks (see [README](README.md)) enforce most of these rules. The rest need a human eye, and are marked **(review)**.

---

## 1. Before you write: one page, one question

Every page answers one main question a real person would type or ask. Write it down before you start.

| Page type | The question it answers | Example |
|---|---|---|
| Product | What is it, who is it for, what do I get, what does it cost? | Fearlessly Unfuckwithable |
| Service | What happens, what do I send, what does it cost, what isn't it? | Energetic Scans |
| Article / guide | One specific question in the reader's own words | "Why does my body still feel on edge when life is calm?" |
| About | Who is Kay Joy Flowers and what is her work? | About |

**Search intent (review).** Match the page to why the person is searching:
- *Learning* ("what is survival mode") → an article that answers in the first paragraph, then goes deeper.
- *Comparing or choosing* ("book on self-trust for women") → a product page with clear contents, format and price.
- *Doing* ("book a remote energy scan") → a service page where the button is in the first screen.

Don't invent keyword volumes. If you want data, use Google Search Console (free) once the site is verified there. It shows the real queries people used to find the site.

## 2. Voice comes first (review)

Kay's voice is grounded, embodied, sovereign, calm, precise and direct. It is never guru-like, manipulative or hype-driven. SEO never overrides that:
- No keyword stuffing. Say the product name naturally, as Kay would.
- No artificial scarcity, countdowns, pop-ups or "only 3 left".
- No invented testimonials, results, credentials, scientific claims or features.
- Health-adjacent pages (Genius Insight) always keep the "what this is and isn't" disclaimer.

## 3. The head of every page

Copy [templates/page-head.html](templates/page-head.html) and fill in every placeholder.

| Element | Rule | Checked automatically |
|---|---|---|
| `<title>` | 15–65 characters, unique. Subject first, brand last: `Topic or product \| Kay Joy Flowers` | yes |
| `<meta name="description">` | 70–160 characters, unique. What the visitor gets, in Kay's words | yes |
| `<link rel="canonical">` | The page's own full URL: `https://kayjoyflowers.online/page.html` (home is `https://kayjoyflowers.online/`) | yes |
| Open Graph | `og:title`, `og:description`, `og:url` (= canonical), `og:type`, `og:image` (+ width, height, alt), `og:locale`, `og:site_name` | yes |
| Twitter/X | `twitter:card` = `summary_large_image`, plus title, description, image and image alt | yes |
| `<meta name="author">` | `Kay Joy Flowers` | yes |
| Favicon links | Copy from the template | no |
| Private pages | Payment-gated, sign-in or test pages get `<meta name="robots" content="noindex, nofollow">` and stay out of the sitemap | yes |

**Share image.** 1200×630. Add an entry to `tools/og-images.json` (eyebrow, headline, sub-line, image) using only words that are already on the page, then run `node tools/make_images.mjs`. The image goes in `images/og/`.

## 4. Headings and structure

- Exactly **one H1** per page, stating the subject.
- Then H2 for sections, H3 inside them. **Never skip a level** (H1 → H3). If a heading needs to look smaller, change it with CSS, not by using a lower level (see `.card h2` in `styles.css`).
- **Answer first (AEO).** Under each H2, the first one or two sentences should answer the heading on their own. That's the sentence an AI answer engine quotes.
- Use real questions as headings where it suits the page ("What do I need to send?").
- Aim for at least 250 words of genuinely useful text on indexable pages. Don't pad.

## 5. Images

- **Alt text** describes the image for someone who can't see it: `Fearlessly Unfuckwithable by Kay Joy Flowers, book cover`, `Portrait of Kay Joy Flowers`. A purely decorative image gets `alt=""` *and* `role="presentation"`.
- Always set `width` and `height` to the image file's real pixel size (this prevents layout jumps).
- The **first large image** on a page: no `loading="lazy"`, and add `fetchpriority="high"`. Every image below the first screen: `loading="lazy"`.
- Size and format: WebP, no wider than about 2× the displayed width. Portraits and covers shown under 400 px wide: 600–800 px source. Aim for under 100 KB.
- Self-host images that appear in the first screen (`images/`). Images further down may stay on the Beacons CDN.

## 6. Internal links

- Every public page is linked from the header nav, the footer, or at least one related page. No orphans.
- Link related things to each other: book ↔ bundle ↔ Companion, Library ↔ each available title, articles → the product they relate to (once, naturally, not in every paragraph).
- Use descriptive link text ("See the book and the bundle"), never "click here".
- The footer on every public page links to: Fearlessly Unfuckwithable, Energetic Scans, The Library, About and Privacy.
- Use relative links (`about.html`) on normal pages. Use root-relative links (`/about.html`) on `404.html`.

## 7. Structured data (JSON-LD)

Copy from [templates/structured-data.md](templates/structured-data.md). Rules:
- One `<script type="application/ld+json">` block per page, using `@graph`.
- Kay is always the same entity: `{"@id": "https://kayjoyflowers.online/#kay"}`. Define her fully on the home and About pages; everywhere else just reference that `@id`.
- **Prices in markup must match the visible price exactly**, including currency. If the page says US$77, the markup says `"price": "77", "priceCurrency": "USD"`.
- **FAQ markup only for questions visible on the page**, word for word.
- Inner pages get a `BreadcrumbList`.
- A book is a `Book` with an `Offer` for the book only. A bundle or other product is its own `Product`. A service (scans) is a `Service` with one `Offer` per price option shown.
- Never mark up reviews, ratings or testimonials that don't exist.

## 8. Commerce pages (review)

- Never change a price, payment link or product without Kay's explicit approval.
- After any change to a page with checkout buttons, click every button once and check it opens the right Beacons or Stripe product at the right price. Automated checks can't get past Beacons' bot protection.
- Say what's included, the format, the currency, and the checkout provider near each button.

## 9. Sitemap, robots and llms.txt

- After committing a new or changed public page, run `python3 tools/build_sitemap.py` and commit `sitemap.xml`. It lists every indexable page with its last-changed date from git. CI fails if the sitemap's list of URLs is out of date.
- `robots.txt` doesn't need changes for new pages.
- `llms.txt` is an optional plain-language map for AI tools, not a ranking factor. Add a line when you add a major page (product, service or cornerstone article), and update it when a price changes.

## 10. Articles and guides (when the blog starts)

- URL: `/articles/short-descriptive-slug.html`. Lowercase with hyphens, no dates in the URL.
- Byline: "By Kay Joy Flowers" with a visible published date and, if updated, an updated date.
- Structured data: `BlogPosting` with `author` → `#kay`, `datePublished`, `dateModified`, `image`, `headline` (see templates).
- Open with a 2–3 sentence direct answer, then the depth. Finish with a natural link to the related book or practice.
- Add the article to the sitemap (automatic with `tools/build_sitemap.py`) and link it from at least one existing page.

## 11. Before you publish: checklist

1. `python3 tools/seo_audit.py --root .` reports no critical or high failures.
2. `python3 tools/build_sitemap.py --check` passes (run `tools/build_sitemap.py` after committing if not).
3. `cd tools/jsonld-check && npm ci && node check.mjs` passes.
4. Open the page on a phone: nothing scrolls sideways, buttons are easy to tap.
5. Click every checkout button. **(review)**
6. Read it aloud once. Does it sound like Kay? **(review)**

CI runs 1–3 automatically on every push and pull request.
