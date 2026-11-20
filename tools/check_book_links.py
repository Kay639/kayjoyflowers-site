"""Validate published book offers and closing links in the built pages."""
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from book_links import BOOKS
from seo_audit import CHECKOUT_HOSTS, PageParser, walk_jsonld

ROOT = Path(__file__).resolve().parent.parent
BUNDLE_PAGE = "/fearlessly-unfuckwithable.html"


def read_page(path):
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def hrefs(page):
    return {attrs.get("href", "") for attrs, *_ in page.anchors}


def has_offer(page, kind, price):
    links = hrefs(page)
    for script in page.jsonld_raw:
        for node in walk_jsonld(json.loads(script)):
            if node.get("@type") != kind:
                continue
            if kind == "Product" and not node.get("@id", "").endswith("#sovereignty-bundle"):
                continue
            offers = node.get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]
            for offer in offers:
                checkout = urlsplit(offer.get("url", ""))
                if (checkout.scheme == "https" and checkout.hostname == "shop.beacons.ai"
                        and offer["url"] in links and str(offer.get("price")) == price
                        and offer.get("priceCurrency") == "USD"
                        and offer.get("availability") == "https://schema.org/InStock"):
                    return True
    return False


class LibraryCards(PageParser):
    """Read each card separately so its status stays associated with its links."""

    def __init__(self):
        super().__init__()
        self.cards = []
        self.card = None
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        if self.card is not None:
            self.card.handle_starttag(tag, attrs)
            if tag == "div":
                self.depth += 1
        elif tag == "div" and "card" in (dict(attrs).get("class") or "").split():
            self.card = PageParser()
            self.depth = 1
        super().handle_starttag(tag, attrs)

    def handle_data(self, data):
        if self.card is not None:
            self.card.handle_data(data)
        super().handle_data(data)

    def handle_endtag(self, tag):
        if self.card is not None:
            if tag == "div":
                self.depth -= 1
            if self.depth:
                self.card.handle_endtag(tag)
            else:
                self.cards.append(self.card)
                self.card = None
        super().handle_endtag(tag)


def main():
    errors = []
    published = set()
    for path in BOOKS:
        page = read_page(ROOT / path.lstrip("/"))
        if has_offer(page, "Book", "33"):
            published.add(path)
        else:
            errors.append(f"{path}: expected a US$33 in-stock Book offer matching a Beacons link")
        if path == BUNDLE_PAGE and not has_offer(page, "Product", "77"):
            errors.append(f"{path}: expected the US$77 in-stock Sovereignty Bundle offer")

    for directory, source in (("blog", "journal"), ("podcast", "podcast")):
        pages = sorted((ROOT / directory).glob("*/index.html"))
        if not pages:
            errors.append(f"{directory}: no content pages found")
        for path in pages:
            links = [
                urlsplit(attrs.get("href", ""))
                for attrs, _, footer, _, nav in read_page(path).anchors
                if "data-book-link" in attrs and not footer and not nav
            ]
            if len(links) != 1 or not (
                not links[0].scheme and not links[0].netloc
                and links[0].path in published
                and parse_qs(links[0].query).get("utm_source") == [source]
            ):
                errors.append(f"{path.relative_to(ROOT)}: expected one tracked closing link to a published book")

    library = LibraryCards()
    library.feed((ROOT / "library.html").read_text(encoding="utf-8"))
    library.close()
    for card in library.cards:
        if not any(part.strip().casefold() == "coming soon" for part in card.text_parts):
            continue
        if any(urlsplit(attrs.get("href", "")).hostname in CHECKOUT_HOSTS
               or re.match(r"\s*(buy|purchase|pre[- ]?order)\b", label, re.I)
               for attrs, label, *_ in card.anchors):
            title = next((text for _, text in card.headings), "Untitled card")
            errors.append(f"library.html: coming-soon book has a buy button ({title})")

    if errors:
        raise SystemExit("\n".join(errors))
    print("Published book offers, tracked closing links and coming-soon cards passed.")


if __name__ == "__main__":
    main()
