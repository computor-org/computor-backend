"""URL construction helpers for generated endpoint clients."""

from urllib.parse import quote


def quote_path(value: object) -> str:
    """Percent-encode a value for use as a single URL path segment.

    ``safe=""`` so that slashes are escaped too: object keys, workspace names
    and repository paths are all legitimate id values that would otherwise
    silently change which route the request hits.
    """
    return quote(str(value), safe="")
