# Structured data templates (JSON-LD)

Put one block per page in the `<head>`, inside a `@graph`. Replace CAPITALS. The live pages are working examples:

| Page | Types used |
|---|---|
| `index.html` | WebSite, Person (full definition) |
| `about.html` | Person, ProfilePage, BreadcrumbList |
| `fearlessly-unfuckwithable.html` | Book (+ Offer), Product (bundle + Offer), BreadcrumbList |
| `genius-insight.html` | Service (+ Offers), FAQPage, BreadcrumbList |
| `library.html`, `privacy.html` | BreadcrumbList |

After editing, run `cd tools/jsonld-check && npm ci && node check.mjs` (schema.org type check) and `python3 tools/seo_audit.py --root .` (required properties, prices match the page, FAQ matches the page).

## Kay (reference only, on every page except home and About)
```json
{"@id": "https://kayjoyflowers.online/#kay"}
```
Use it as the value of `author`, `provider` or `publisher`. Don't redefine Kay on other pages. If her details change (new social profile, new book), update the Person node in **both** `index.html` and `about.html`.

## Breadcrumbs (every inner page)
```json
{
 "@type": "BreadcrumbList",
 "itemListElement": [
  {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://kayjoyflowers.online/"},
  {"@type": "ListItem", "position": 2, "name": "PAGE NAME", "item": "https://kayjoyflowers.online/PAGE.html"}
 ]
}
```

## A book
```json
{
 "@type": "Book",
 "@id": "https://kayjoyflowers.online/PAGE.html#book",
 "name": "BOOK TITLE",
 "author": {"@id": "https://kayjoyflowers.online/#kay"},
 "image": "https://kayjoyflowers.online/images/COVER.webp",
 "bookFormat": "https://schema.org/EBook",
 "inLanguage": "en",
 "url": "https://kayjoyflowers.online/PAGE.html",
 "description": "ONE OR TWO SENTENCES FROM THE PAGE.",
 "offers": {
  "@type": "Offer",
  "name": "BOOK TITLE (digital book)",
  "price": "33",
  "priceCurrency": "USD",
  "availability": "https://schema.org/InStock",
  "url": "https://shop.beacons.ai/kayjoyflowers/PRODUCT-ID"
 }
}
```
For a book that isn't out yet, leave out `offers` (don't use `PreOrder` unless pre-orders are actually open).

## A bundle, course or other product
```json
{
 "@type": "Product",
 "@id": "https://kayjoyflowers.online/PAGE.html#SLUG",
 "name": "PRODUCT NAME",
 "description": "WHAT'S INCLUDED, FROM THE PAGE.",
 "image": "IMAGE URL",
 "isRelatedTo": {"@id": "https://kayjoyflowers.online/PAGE.html#book"},
 "offers": {"@type": "Offer", "price": "77", "priceCurrency": "USD", "availability": "https://schema.org/InStock", "url": "CHECKOUT URL"}
}
```

## A service
```json
{
 "@type": "Service",
 "@id": "https://kayjoyflowers.online/PAGE.html#service",
 "name": "SERVICE NAME",
 "provider": {"@id": "https://kayjoyflowers.online/#kay"},
 "serviceType": "WHAT KIND OF SERVICE",
 "areaServed": "Worldwide",
 "url": "https://kayjoyflowers.online/PAGE.html",
 "offers": [
  {"@type": "Offer", "name": "OPTION", "price": "100", "priceCurrency": "USD", "availability": "https://schema.org/InStock", "url": "CHECKOUT URL"},
  {"@type": "Offer", "name": "MONTHLY OPTION", "price": "120", "priceCurrency": "USD", "url": "CHECKOUT URL",
   "priceSpecification": {"@type": "UnitPriceSpecification", "price": "120", "priceCurrency": "USD", "unitText": "month", "unitCode": "MON"}}
 ]
}
```
Add one Offer per price option the page shows (other currencies included).

## FAQ (only questions visible on the page, word for word)
```json
{
 "@type": "FAQPage",
 "mainEntity": [
  {"@type": "Question", "name": "THE VISIBLE QUESTION?",
   "acceptedAnswer": {"@type": "Answer", "text": "THE VISIBLE ANSWER, WITHOUT LINKS."}}
 ]
}
```

## An article or guide
```json
{
 "@type": "BlogPosting",
 "@id": "https://kayjoyflowers.online/articles/SLUG.html#article",
 "headline": "THE H1",
 "description": "THE META DESCRIPTION",
 "author": {"@id": "https://kayjoyflowers.online/#kay"},
 "publisher": {"@id": "https://kayjoyflowers.online/#kay"},
 "datePublished": "2026-01-31",
 "dateModified": "2026-01-31",
 "image": "https://kayjoyflowers.online/images/og/SLUG.jpg",
 "mainEntityOfPage": "https://kayjoyflowers.online/articles/SLUG.html",
 "inLanguage": "en"
}
```
For a full article page, also add the BreadcrumbList (Home → Articles → title) and the reference to Kay.
