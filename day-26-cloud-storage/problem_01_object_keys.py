"""Problem 1 — object keys are paths, not files.

THE PROBLEM (beginner foothold first)
------------------------------------
Object storage has no folders. A "folder" like ``raw/events/`` is just
a shared prefix on flat keys: ``raw/events/2026/10/29/part-0001.parquet``.
Two pipelines that disagree about key spelling — one writes
``Raw/Events/`` with capitals, another lists prefix ``raw/`` — silently
see different datasets, and a downstream job reads an empty prefix and
reports "no data" instead of "wrong prefix".

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - A key is a non-empty string, 1..1024 bytes long, with no leading
    slash, no backslash, no control characters, no empty segment
    (``//``), and no ``.`` or ``..`` segment. A trailing slash marks a
    prefix placeholder, not an object, so it is not a valid object key.
  - Listing is prefix + delimiter based: ``list_objects`` with
    ``delimiter="/"`` rolls keys sharing the next segment into
    ``common_prefixes`` (the "folders"), exactly like an S3
    ListObjectsV2 call; without a delimiter it returns flat keys.
  - Listing is paginated: ``max_keys`` caps a page and a non-None
    ``next_token`` means more results exist. A token that does not
    name a key in the listing is a caller bug, not an empty page.
  - Keys sort in plain byte order, so ``part-10`` sorts before
    ``part-2`` — partition writers must zero-pad sequence numbers.

Plain words: the key IS the address — spell it by contract, list by
prefix, and page like the API does, or two jobs will quietly disagree
about what exists.
"""

MAX_KEY_LENGTH = 1024


class KeyError_(ValueError):
    """Raised for an invalid key, prefix, or pagination token."""


def validate_key(key):
    """Return True if ``key`` is a valid object key under the contract.

    Anything else — not a string, empty, too long, a leading slash, a
    backslash, a control character, an empty segment, a ``.``/``..``
    segment, or a trailing slash — returns False instead of raising,
    so callers can collect bad keys from a batch.
    """
    if not isinstance(key, str):
        return False
    if not key or len(key.encode("utf-8")) > MAX_KEY_LENGTH:
        return False
    if key.startswith("/") or key.endswith("/") or "\\" in key:
        return False
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in key):
        return False
    segments = key.split("/")
    if any(seg in ("", ".", "..") for seg in segments):
        return False
    return True


class ObjectStore:
    """A flat dict-backed object store: keys map to bytes, nothing more."""

    def __init__(self):
        self._objects = {}

    def put(self, key, data):
        if not validate_key(key):
            raise KeyError_(f"invalid object key: {key!r}")
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("object data must be bytes")
        self._objects[key] = bytes(data)

    def get(self, key):
        try:
            return self._objects[key]
        except KeyError:
            raise KeyError(f"no such object: {key!r}") from None

    def exists(self, key):
        return key in self._objects

    def delete(self, key):
        self._objects.pop(key, None)

    def keys(self):
        return sorted(self._objects)


def list_objects(store, prefix="", delimiter=None, max_keys=1000,
                 continuation_token=None):
    """List one page of ``store`` under ``prefix``.

    Returns ``(keys, common_prefixes, next_token)``. Pagination runs
    over the matching keys in sorted order, exactly like an S3
    ListObjectsV2 call: the page holds the next ``max_keys`` matching
    keys, and prefixes are derived from that page alone. With
    ``delimiter`` set, a page key whose remainder past the prefix
    contains the delimiter rolls up into ``common_prefixes`` (prefix +
    first segment + delimiter, deduplicated and sorted) instead of
    appearing in ``keys``. ``max_keys`` must be a positive int;
    ``continuation_token`` must be a key already returned by a
    previous page of this same listing, otherwise ``KeyError_`` is
    raised. ``next_token`` is the last key of this page, or None when
    the listing is exhausted.
    """
    if not isinstance(max_keys, int) or isinstance(max_keys, bool) \
            or max_keys < 1:
        raise KeyError_("max_keys must be a positive int")
    all_keys = [k for k in store.keys() if k.startswith(prefix)]
    if continuation_token is not None:
        if continuation_token not in all_keys:
            raise KeyError_(f"unknown continuation token: {continuation_token!r}")
        start = all_keys.index(continuation_token) + 1
    else:
        start = 0
    page_keys = all_keys[start:start + max_keys]
    keys, prefixes = [], []
    seen_prefixes = set()
    for key in page_keys:
        rest = key[len(prefix):]
        if delimiter is not None and delimiter in rest:
            rolled = prefix + rest.split(delimiter, 1)[0] + delimiter
            if rolled not in seen_prefixes:
                seen_prefixes.add(rolled)
                prefixes.append(rolled)
            continue
        keys.append(key)
    next_token = page_keys[-1] if start + max_keys < len(all_keys) else None
    return keys, sorted(prefixes), next_token
