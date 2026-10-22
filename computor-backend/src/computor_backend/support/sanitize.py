"""Server-side HTML sanitising for mail shown in the ticket view.

Mail HTML is untrusted. It is reduced to an allowlist of formatting tags with
no styles, no images and no remote references of any kind, so rendering it
cannot load anything, run anything or track the reader. The UI additionally
shows it only inside a sandboxed iframe with a ``default-src 'none'`` CSP.
"""
import html as html_lib
import re

import nh3

ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "caption", "code", "dd", "del", "div",
    "dl", "dt", "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "ins", "kbd",
    "li", "ol", "p", "pre", "q", "s", "small", "span", "strong", "sub", "sup",
    "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
}
# No style/class/id: CSS can fetch (url(), @import) and ids can clobber.
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "td": {"colspan", "rowspan", "align", "valign"},
    "th": {"colspan", "rowspan", "align", "valign", "scope"},
    "abbr": {"title"},
}
# Content removed together with the tag.
DROP_WITH_CONTENT = {"script", "style", "head", "title", "template", "noscript",
                     "iframe", "object", "embed", "svg", "math", "frameset"}
URL_SCHEMES = {"http", "https", "mailto"}

MAX_HTML_CHARS = 1_000_000


def sanitize_html(raw: str) -> str:
    """Allowlist-sanitised HTML fragment (links kept, nothing loadable)."""
    if not raw:
        return ""
    raw = raw[:MAX_HTML_CHARS]
    return nh3.clean(
        raw,
        tags=ALLOWED_TAGS,
        clean_content_tags=DROP_WITH_CONTENT,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=URL_SCHEMES,
        link_rel="noopener noreferrer nofollow",
        set_tag_attribute_values={"a": {"target": "_blank"}},
        strip_comments=True,
    )


_BLOCK_END = re.compile(r"(?i)<\s*(br\s*/?|/p|/div|/tr|/li|/h[1-6]|/blockquote|/pre|/table)\s*>")
_CELL_END = re.compile(r"(?i)<\s*/t[dh]\s*>")
_BLANK_LINES = re.compile(r"\n{3,}")


def html_to_text(raw: str) -> str:
    """Plain-text rendering of mail HTML (for mails without a text part)."""
    if not raw:
        return ""
    raw = raw[:MAX_HTML_CHARS]
    marked = _CELL_END.sub("\t", _BLOCK_END.sub("\n", raw))
    stripped = nh3.clean(marked, tags=set(), clean_content_tags=DROP_WITH_CONTENT)
    text = html_lib.unescape(stripped)
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()
