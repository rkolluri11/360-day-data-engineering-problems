"""Problem 4 — tiers and lifecycle: cold data should cost cold money.

THE PROBLEM (beginner foothold first)
------------------------------------
Hot storage answers in milliseconds and charges like it; archive
storage costs almost nothing and answers in hours. A pipeline that
leaves last year's raw exports on Hot pays Hot prices for data nobody
reads, while a pipeline that archives yesterday's serving table breaks
every dashboard that queries it.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Tier order is fixed and one-way for lifecycle: Hot -> Cool ->
    Archive. A rule that "transitions" Archive back to Hot, or repeats
    a tier, is a config bug caught at rule validation, not at bill time.
  - Transition ages must strictly increase, and an expiration age
    must be later than the last transition — expiring an object before
    it ever transitions is a rule that fights itself.
  - A rule applies only to keys under its prefix; an empty prefix
    means the whole bucket, and that breadth must be explicit in the
    rule, not an accident of a missing field.
  - ``apply_lifecycle`` reports the tier an object sits in at its age
    and whether it is expired — it never deletes anything itself, so
    the caller owns the destructive step.
  - Monthly cost is tier price per GiB-month times size; archive
    retrieval is priced by retrieval speed (expedited / standard /
    bulk) and takes model hours — Hot and Cool restore instantly.
    These are model prices for the exercise, not a vendor price list.

Plain words: data cools with age — move it down the tiers on a
schedule you can read, price the move before you make it, and never
let the lifecycle delete what the transition was supposed to save.
"""

TIER_ORDER = ("Hot", "Cool", "Archive")
PRICE_PER_GIB_MONTH = {"Hot": 0.020, "Cool": 0.010, "Archive": 0.001}
RETRIEVAL_HOURS = {
    ("Hot", "expedited"): 0, ("Hot", "standard"): 0, ("Hot", "bulk"): 0,
    ("Cool", "expedited"): 0, ("Cool", "standard"): 0, ("Cool", "bulk"): 0,
    ("Archive", "expedited"): 1, ("Archive", "standard"): 12,
    ("Archive", "bulk"): 48,
}


class LifecycleError(ValueError):
    """Raised for a malformed lifecycle rule."""


def validate_rule(rule):
    """Return True if ``rule`` is a well-formed lifecycle rule.

    A rule is a dict with a ``prefix`` string, a ``transitions`` list
    of ``(age_days, tier)`` pairs with strictly increasing ages moving
    strictly colder through TIER_ORDER, and an optional
    ``expiration_days`` later than the last transition age. An empty
    transitions list is valid (expire-only rules exist); a rule with
    no ``prefix`` key is not.
    """
    if not isinstance(rule, dict) or "prefix" not in rule:
        return False
    if not isinstance(rule["prefix"], str):
        return False
    transitions = rule.get("transitions", [])
    if not isinstance(transitions, list):
        return False
    last_age, last_tier_idx = -1, -1
    for item in transitions:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            return False
        age, tier = item
        if not isinstance(age, int) or isinstance(age, bool) or age < 0:
            return False
        if tier not in TIER_ORDER:
            return False
        tier_idx = TIER_ORDER.index(tier)
        if age <= last_age or tier_idx <= last_tier_idx:
            return False
        last_age, last_tier_idx = age, tier_idx
    expiration = rule.get("expiration_days")
    if expiration is not None:
        if not isinstance(expiration, int) or isinstance(expiration, bool) \
                or expiration <= 0:
            return False
        if transitions and expiration <= last_age:
            return False
    return True


def apply_lifecycle(key, age_days, rule):
    """Return ``(tier, expired)`` for an object of ``age_days``.

    Objects outside the rule's prefix stay Hot and unexpired. Inside
    the prefix, the tier is the last transition whose age has been
    reached (Hot before the first), and ``expired`` is True once
    ``age_days`` reaches ``expiration_days``. Raises LifecycleError
    for a malformed rule.
    """
    if not validate_rule(rule):
        raise LifecycleError(f"malformed lifecycle rule: {rule!r}")
    if not key.startswith(rule["prefix"]):
        return "Hot", False
    tier = "Hot"
    for age, next_tier in rule.get("transitions", []):
        if age_days >= age:
            tier = next_tier
    expiration = rule.get("expiration_days")
    expired = expiration is not None and age_days >= expiration
    return tier, expired


def monthly_cost(size_gib, tier):
    """Return the model monthly cost of ``size_gib`` GiB on ``tier``."""
    if tier not in PRICE_PER_GIB_MONTH:
        raise LifecycleError(f"unknown tier: {tier!r}")
    if size_gib < 0:
        raise LifecycleError("size_gib must be non-negative")
    return size_gib * PRICE_PER_GIB_MONTH[tier]


def restore_time_hours(tier, retrieval):
    """Return model restore hours for ``tier`` at ``retrieval`` speed."""
    try:
        return RETRIEVAL_HOURS[(tier, retrieval)]
    except KeyError:
        raise LifecycleError(
            f"unknown tier/retrieval pair: {tier!r}/{retrieval!r}") from None
