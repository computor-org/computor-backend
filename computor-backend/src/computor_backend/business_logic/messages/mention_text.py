"""Resolve plain @names in Markdown prose without touching literal/code text."""
import re
from collections.abc import Callable


TUTOR_ALIASES = ("lena", "luna", "ai")
TOKEN = re.compile(r"(?<![\w@.+-])@([\w][\w.-]*)", re.UNICODE)
STRUCTURED = re.compile(r"@\[[^\]]*\]\([0-9a-fA-F-]{36}\)")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def prose_mask(content: str) -> list[bool]:
    """Mark Markdown code and existing UUID mentions as protected spans."""
    mask = [True] * len(content)
    fence = None
    offset = 0
    for line in content.splitlines(keepends=True):
        marker = FENCE.match(line)
        protected = fence is not None or marker is not None or line.startswith(("    ", "\t"))
        if fence is not None:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
        elif marker:
            fence = marker[1]
        if protected:
            mask[offset:offset + len(line)] = [False] * len(line)
        offset += len(line)
    # Inline code can contain newlines and uses matching backtick-run lengths.
    ticks = list(re.finditer(r"`+", content))
    i = 0
    while i < len(ticks):
        start = ticks[i]
        if not mask[start.start()] or _escaped(content, start.start()):
            i += 1
            continue
        end = next((j for j in range(i + 1, len(ticks))
                    if mask[ticks[j].start()] and ticks[j][0] == start[0]), None)
        if end is None:
            i += 1
            continue
        last = ticks[end].end()
        mask[start.start():last] = [False] * (last - start.start())
        i = end + 1
    for match in STRUCTURED.finditer(content):
        mask[match.start():match.end()] = [False] * len(match[0])
    return mask


def _escaped(content: str, position: int) -> bool:
    before = content[:position]
    return (len(before) - len(before.rstrip("\\"))) % 2 == 1


def resolve_plain_mentions(content: str, lookup: Callable[[str], tuple[str, str] | None]) -> str:
    """Replace eligible complete @tokens with canonical UUID mention tokens.

    The caller resolves identities against the full audience, never a limited
    autocomplete page. Unknown names stay visibly unlinked; ambiguous names
    are reported by the caller rather than picking an arbitrary recipient.
    """
    mask = prose_mask(content)

    def replace(match: re.Match) -> str:
        if not all(mask[match.start():match.end()]) or _escaped(content, match.start()):
            return match[0]
        # A sentence-ending period is punctuation, not part of the handle.
        name = match[1].rstrip(".")
        trailing = match[1][len(name):]
        if not name or (match.end() < len(content) and content[match.end()] == "@"):
            return match[0]
        target = lookup(name.casefold())
        if target is None:
            return match[0]
        user_id, display = target
        display = display.replace("]", "").replace("\n", " ")
        return f"@[{display}]({user_id}){trailing}"

    return TOKEN.sub(replace, content)
