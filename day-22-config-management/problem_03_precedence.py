"""Problem 3 — one documented precedence, no surprises
=======================================================

THE PROBLEM (beginner foothold first)
------------------------------------
Config comes from four places: code defaults, a YAML file of
shared defaults, environment variables, and a secrets manager.
When two places set the same key, everyone on the team must know
which one wins — otherwise the prod run quietly uses the staging
value and nobody can say why.

The documented order, weakest to strongest:

    defaults < YAML file < environment variables < secrets

Each layer overrides only the keys it sets; the rest fall through
to the layer below. Nested mappings merge key-by-key (a YAML file
that sets only ``database.port`` must not wipe out the default
``database.host``).

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Merge is DEEP, not shallow: replacing a whole nested dict
    when one key changes is how a YAML tweak silently drops the
    default host. ``deep_merge`` recurses into dicts and replaces
    everything else (a list is replaced whole — merging lists
    element-wise is a guessing game).
  - YAML here is a small, explicit subset — ``key: value`` lines,
    two-space indented nesting, ``#`` comments, and plain scalars
    (ints, floats, booleans, quoted strings). No PyYAML dependency:
    the repo stays stdlib-only, and a 40-line parser whose failure
    modes you can read beats a library you cannot audit for a
    config file this shape. Malformed lines raise ``ConfigError``.
  - Env keys are flat (``DB_HOST``), YAML keys are nested
    (``database: {host: ...}``) — ``resolve`` flattens the merged
    result with the documented precedence, and env wins over YAML
    even when YAML was loaded second.
  - The merge never mutates its inputs: layer dicts are copied on
    the way in, so a caller reusing a defaults dict across
    environments cannot poison the next resolve.

Plain words: precedence is a stack of transparencies. Each sheet
adds its own ink; the top sheet is what you see. Nobody has to
guess which sheet is on top — it is written on the box.
"""

from problem_01_env_not_code import ConfigError


def deep_merge(base, override):
    """Merge two dicts: override wins key-by-key, dicts recurse."""
    merged = dict(base)
    for key, value in override.items():
        if (key in merged and isinstance(merged[key], dict)
                and isinstance(value, dict)):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _scalar(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    lowered = text.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    if lowered in ("null", "~"):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def parse_yaml(text):
    """Parse the small YAML subset described above into a dict."""
    root = {}
    stack = [(-1, root)]  # (indent level, dict)
    for lineno, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2:
            raise ConfigError(f"line {lineno}: indent must be a multiple of 2")
        if ":" not in line:
            raise ConfigError(f"line {lineno}: expected 'key: value'")
        key, _, value = line.strip().partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ConfigError(f"line {lineno}: empty key")
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if key in parent:
            raise ConfigError(f"line {lineno}: duplicate key {key!r}")
        if value == "":
            child = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _scalar(value)
    return root


def resolve(defaults, yaml_text="", env=None, secrets=None):
    """Resolve config with precedence: defaults < YAML < env < secrets.

    ``env`` and ``secrets`` are flat key/value mappings whose keys
    are uppercased, underscore-joined paths (``DATABASE_HOST`` maps
    to ``database.host``). Returns the merged nested dict.
    """
    merged = dict(defaults)
    if yaml_text:
        merged = deep_merge(merged, parse_yaml(yaml_text))
    for layer in (env or {}, secrets or {}):
        nested = {}
        for flat_key, value in layer.items():
            parts = flat_key.lower().split("_")
            cursor = nested
            for part in parts[:-1]:
                cursor = cursor.setdefault(part, {})
            cursor[parts[-1]] = value
        merged = deep_merge(merged, nested)
    return merged
