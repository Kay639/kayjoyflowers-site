"""Published sales pages and their existing closing-link copy."""
from html import escape
from urllib.parse import urlencode

BOOKS = {
    "/fearlessly-unfuckwithable.html": (
        "Fearlessly Unfuckwithable",
        "An Embodied Experience of descent, self-trust and radical self-ownership",
    ),
    "/medicine-woman.html": ("Medicine Woman", "A Path of Remembrance"),
    "/frequency.html": ("Frequency", "The Future of Medicine"),
}


def book_link(path, source, slug):
    title, subtitle = BOOKS[path]
    query = urlencode({"utm_source": source, "utm_medium": "website", "utm_content": slug})
    destination = f"{path}?{query}"
    if path == "/fearlessly-unfuckwithable.html":
        destination += "#offers"
    return (f'<p class="cta"><a class="btn primary" data-book-link href="{escape(destination)}">'
            f'{escape(title)} — {escape(subtitle)}</a></p>')
