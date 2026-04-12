"""Bidding languages for combinatorial auctions.

Supports four standard bidding languages used in the literature:

- **XOR bids**: bidder can win at most one bundle.
- **OR bids**: bidder can win any non-overlapping combination of bundles
  (additive across non-conflicting bids).
- **Additive-OR bids**: OR bids where the bidder has additive valuations
  over individual items.
- **Bundle bids**: simple single-bundle bids (the default).

Each language class converts a high-level bid expression into a list of
atomic Bid objects suitable for the WDP solver.
"""

from __future__ import annotations

from src.core.auction import Bid, Bidder


class BundleBid:
    """A single bundle bid -- the simplest bidding language.

    The bidder specifies one bundle and one value.
    """

    def __init__(self, bidder_id: str, bundle: frozenset[str], value: float):
        self.bidder_id = bidder_id
        self.bundle = bundle
        self.value = value

    def to_bids(self) -> list[Bid]:
        return [
            Bid(
                bidder_id=self.bidder_id,
                bundle=self.bundle,
                value=self.value,
                bid_id=f"{self.bidder_id}_bundle_0",
            )
        ]


class XORBid:
    """XOR bidding language: the bidder can win at most one of the listed bundles.

    To enforce the XOR constraint in a standard WDP, we add a dummy item
    unique to this bidder to every bid.  Since each item can be allocated
    at most once, at most one of the XOR bids can win.
    """

    def __init__(self, bidder_id: str):
        self.bidder_id = bidder_id
        self.bundles: list[tuple[frozenset[str], float]] = []

    def add(self, bundle: frozenset[str], value: float) -> XORBid:
        """Add a bundle-value pair to this XOR bid."""
        self.bundles.append((bundle, value))
        return self

    def to_bids(self) -> list[Bid]:
        """Convert to atomic bids with a dummy XOR-enforcement item."""
        dummy = f"__xor_dummy_{self.bidder_id}__"
        bids: list[Bid] = []
        for idx, (bundle, value) in enumerate(self.bundles):
            augmented_bundle = bundle | frozenset([dummy])
            bids.append(
                Bid(
                    bidder_id=self.bidder_id,
                    bundle=augmented_bundle,
                    value=value,
                    bid_id=f"{self.bidder_id}_xor_{idx}",
                )
            )
        return bids

    def dummy_items(self) -> frozenset[str]:
        """Return the set of dummy items introduced by this XOR bid."""
        return frozenset([f"__xor_dummy_{self.bidder_id}__"])


class ORBid:
    """OR bidding language: the bidder can win any non-overlapping combination.

    Under OR semantics, the bidder's value for a collection of won bids is
    the sum of their individual values, as long as the bundles don't overlap.
    This is directly expressible in the standard WDP without modification --
    the item-disjointness constraint of the WDP naturally enforces it.
    """

    def __init__(self, bidder_id: str):
        self.bidder_id = bidder_id
        self.bundles: list[tuple[frozenset[str], float]] = []

    def add(self, bundle: frozenset[str], value: float) -> ORBid:
        """Add a bundle-value pair to this OR bid."""
        self.bundles.append((bundle, value))
        return self

    def to_bids(self) -> list[Bid]:
        """Convert to atomic bids (no transformation needed for OR)."""
        bids: list[Bid] = []
        for idx, (bundle, value) in enumerate(self.bundles):
            bids.append(
                Bid(
                    bidder_id=self.bidder_id,
                    bundle=bundle,
                    value=value,
                    bid_id=f"{self.bidder_id}_or_{idx}",
                )
            )
        return bids


class AdditiveORBid:
    """Additive-OR bidding language: the bidder has an additive valuation.

    The bidder specifies a value for each individual item.  The value of
    any bundle is the sum of the item values.  This generates one
    single-item bid per item, and the OR semantics of the WDP allow
    winning any non-overlapping subset.
    """

    def __init__(self, bidder_id: str):
        self.bidder_id = bidder_id
        self.item_values: list[tuple[str, float]] = []

    def add(self, item: str, value: float) -> AdditiveORBid:
        """Set the value for a single item."""
        self.item_values.append((item, value))
        return self

    def to_bids(self) -> list[Bid]:
        """Generate one single-item bid per item."""
        bids: list[Bid] = []
        for idx, (item, value) in enumerate(self.item_values):
            bids.append(
                Bid(
                    bidder_id=self.bidder_id,
                    bundle=frozenset([item]),
                    value=value,
                    bid_id=f"{self.bidder_id}_addor_{idx}",
                )
            )
        return bids


def apply_bidding_language(bidder: Bidder, language_bid) -> None:
    """Apply a bidding language expression to a Bidder, populating its bids.

    Args:
        bidder: the Bidder to populate.
        language_bid: one of XORBid, ORBid, AdditiveORBid, or BundleBid.
    """
    for bid in language_bid.to_bids():
        bidder.bids.append(bid)
