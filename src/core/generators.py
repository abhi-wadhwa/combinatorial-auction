"""Synthetic demand generators for combinatorial auction experiments.

Provides four standard bidder types from the auction theory literature:

- **Additive**: value of a bundle = sum of individual item values.
- **Substitutes**: items are substitutes; marginal value of additional
  items decreases (sub-additive).
- **Complements**: items are complements; value of the bundle exceeds
  the sum of parts (super-additive).
- **Single-minded**: the bidder wants exactly one specific bundle and
  values nothing else.

Also provides a convenience function to generate a complete random auction.
"""

from __future__ import annotations

import random
from itertools import combinations

from src.core.auction import Auction, Bidder


def generate_additive_bidder(
    bidder_id: str,
    items: list[str],
    value_range: tuple[float, float] = (1.0, 10.0),
    rng: random.Random | None = None,
) -> Bidder:
    """Create a bidder with additive valuations.

    Each item gets an independent random value; bundle value = sum.
    Generates single-item bids (under OR semantics, the solver can
    combine them freely).
    """
    rng = rng or random.Random()
    bidder = Bidder(bidder_id=bidder_id)

    for item in items:
        v = round(rng.uniform(*value_range), 2)
        bidder.add_bid(frozenset([item]), v)

    return bidder


def generate_substitutes_bidder(
    bidder_id: str,
    items: list[str],
    value_range: tuple[float, float] = (5.0, 15.0),
    discount: float = 0.3,
    max_bundle_size: int = 3,
    rng: random.Random | None = None,
) -> Bidder:
    """Create a bidder with substitute valuations.

    For bundles of size k, the total value is discounted by
    (1 - discount)^(k-1) relative to the sum of individual values.
    This captures diminishing marginal returns.

    Args:
        discount: fraction by which each additional item's marginal
            value is reduced.
        max_bundle_size: largest bundle to generate bids for.
    """
    rng = rng or random.Random()
    bidder = Bidder(bidder_id=bidder_id)

    # Generate base item values
    item_values = {item: round(rng.uniform(*value_range), 2) for item in items}

    # Generate bids for bundles up to max_bundle_size
    for size in range(1, min(max_bundle_size, len(items)) + 1):
        for combo in combinations(items, size):
            bundle = frozenset(combo)
            # Sub-additive: discount grows with bundle size
            raw_sum = sum(item_values[i] for i in combo)
            discounted = raw_sum * ((1.0 - discount) ** (size - 1))
            bidder.add_bid(bundle, round(discounted, 2))

    return bidder


def generate_complements_bidder(
    bidder_id: str,
    items: list[str],
    value_range: tuple[float, float] = (3.0, 8.0),
    synergy: float = 0.5,
    target_bundle: frozenset[str] | None = None,
    rng: random.Random | None = None,
) -> Bidder:
    """Create a bidder with complementary valuations.

    The bidder has a target bundle where synergies exist.  Subsets of
    the target bundle get a synergy bonus proportional to how close
    they are to the full target.  Items outside the target bundle have
    only their base value.

    Args:
        synergy: bonus multiplier for the complete target bundle.
            A bundle of size k out of target size T gets a synergy
            bonus of synergy * (k / T).
        target_bundle: the bundle with complementarities.  If None,
            a random subset of items is chosen.
    """
    rng = rng or random.Random()
    bidder = Bidder(bidder_id=bidder_id)

    if target_bundle is None:
        # Pick a random subset of 2 to len(items) items
        size = rng.randint(2, max(2, len(items)))
        target_bundle = frozenset(rng.sample(items, min(size, len(items))))

    target_size = len(target_bundle)
    item_values = {item: round(rng.uniform(*value_range), 2) for item in items}

    # Generate bids for subsets of the target bundle
    target_list = sorted(target_bundle)
    for size in range(1, target_size + 1):
        for combo in combinations(target_list, size):
            bundle = frozenset(combo)
            raw_sum = sum(item_values[i] for i in combo)
            # Super-additive synergy
            bonus = 1.0 + synergy * (size / target_size)
            value = round(raw_sum * bonus, 2)
            bidder.add_bid(bundle, value)

    # Also bid on individual items not in the target
    for item in items:
        if item not in target_bundle:
            bidder.add_bid(frozenset([item]), item_values[item])

    return bidder


def generate_single_minded_bidder(
    bidder_id: str,
    items: list[str],
    bundle_size: int = 2,
    value_range: tuple[float, float] = (10.0, 50.0),
    rng: random.Random | None = None,
) -> Bidder:
    """Create a single-minded bidder.

    The bidder wants exactly one specific bundle and assigns zero value
    to every other bundle.  This is the simplest bidder type and
    corresponds to a single atomic bid.

    Args:
        bundle_size: number of items in the desired bundle.
    """
    rng = rng or random.Random()
    bidder = Bidder(bidder_id=bidder_id)

    actual_size = min(bundle_size, len(items))
    bundle = frozenset(rng.sample(items, actual_size))
    value = round(rng.uniform(*value_range), 2)
    bidder.add_bid(bundle, value)

    return bidder


def generate_random_auction(
    n_items: int = 5,
    n_bidders: int = 4,
    bidder_types: list[str] | None = None,
    seed: int | None = None,
) -> Auction:
    """Generate a complete random auction instance.

    Args:
        n_items: number of items.
        n_bidders: number of bidders.
        bidder_types: list of bidder type strings to cycle through.
            Valid types: "additive", "substitutes", "complements",
            "single_minded".  If None, a mix is used.
        seed: random seed for reproducibility.

    Returns:
        A fully populated Auction.
    """
    rng = random.Random(seed)

    if bidder_types is None:
        bidder_types = ["additive", "substitutes", "complements", "single_minded"]

    items = [f"item_{i}" for i in range(n_items)]
    auction = Auction(items=set(items))

    generators = {
        "additive": generate_additive_bidder,
        "substitutes": generate_substitutes_bidder,
        "complements": generate_complements_bidder,
        "single_minded": generate_single_minded_bidder,
    }

    for i in range(n_bidders):
        bidder_id = f"bidder_{i}"
        btype = bidder_types[i % len(bidder_types)]

        gen_func = generators[btype]
        bidder = gen_func(bidder_id=bidder_id, items=items, rng=rng)
        auction.bidders[bidder_id] = bidder

    return auction
