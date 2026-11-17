# DRAFT, not applied: FAQ for the Fearlessly Unfuckwithable page

**Status:** waiting for Kay's approval. Nothing on this page is live or committed to the page itself.

**Why:** AI answer engines (ChatGPT Search, Perplexity, Google AI Overviews) quote short, direct answers to the questions people actually ask. The flagship page has the facts, but they are spread across sections. A short FAQ puts them in one quotable place. FAQ markup must match visible text word for word, so it is only added if the visible FAQ is.

**Rules used:** every answer comes from text already on kayjoyflowers.online (source in brackets). No new claims, prices, features or outcomes. Kay should rewrite anything that doesn't sound like her.

**Proposed placement:** a new section between "The Unfuckwithable Companion" and the closing "Special launch price" band, styled like the existing FAQ on the Energetic Scans page (`<section class="faq">` with `<details>`).

---

### Questions and answers

**What is Fearlessly Unfuckwithable?**
A book by Kay Joy Flowers: an embodied experience of descent, self-trust and radical self-ownership. Part I is the descent. Part II is the embodied experience.
*(home page; "Inside the book" section)*

**Who is it for?**
Women who know what they should do but still find themselves thrown off course by pressure, other people's expectations, self-doubt, emotional upheaval or circumstances beyond their control.
*("Who this is for" section)*

**What format is the book, and how do I get it?**
It's a digital book. You buy it through a secure checkout on Beacons and get instant access, so you can read it on any device.
*(offer card: "Secure checkout on Beacons. Instant digital access."; book page: "Instant download · read on any device")*

**How much does it cost?**
The book is US$33. The Sovereignty Bundle is US$77 at its special launch price. All prices are in US dollars.
*(offer cards and price notes)*

**What's in the Sovereignty Bundle?**
The book, the 7-Day Survival to Sovereignty Reset and Reset Journal, the FU Somatic Arsenal (ten body-first practices for real moments, chosen by how you feel) and the Unfuckwithable Companion.
*(bundle card)*

**What is the Unfuckwithable Companion?**
An interactive space that holds the 7-Day Reset and the Somatic Arsenal in one place. You write your answers, read them back, and on Day 7 see what you wrote on Day 1 beside who you are now. Your writing is saved in your own browser and isn't sent to Kay or anyone else.
*(Companion section; privacy policy)*

**Is this therapy?**
No. Fearlessly Unfuckwithable is not therapy, diagnosis or emergency support. It is a practice of recognition and embodied awareness, alongside whatever care you already have.
*("What this is not", verbatim)*

---

### Questions deliberately left out (need Kay's answer first)
- Refund policy for the book and bundle (not stated anywhere on the site).
- Page count or reading time (not stated).
- Whether the bundle can be bought as an upgrade after buying the book at a reduced price (not stated; book.html says "Upgrade to the Bundle — US$77").

### If approved
1. Add the visible FAQ section to `fearlessly-unfuckwithable.html`.
2. Add a matching `FAQPage` node to that page's JSON-LD `@graph` (same question and answer text, without the source notes).
3. Run `python3 tools/seo_audit.py --root .`: the `faq_visible` check confirms the markup matches the page.
