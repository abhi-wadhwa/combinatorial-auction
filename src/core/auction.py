"""Auction data structures for combinatorial auctions.

Defines the fundamental objects: items, bids, bidders, auction instances,
and allocation results.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Item:
    """An indivisible item in the auction."""

    name: str

    def __repr__(self) -> str:
        return f"Item({self.name!r})"


@dataclass(frozen=True)
class Bid:
    """A single atomic bid: a bundle of items with an associated value.

    Attributes:
        bidder_id: identifier of the bidder who placed this bid.
        bundle: frozenset of item names included in this bid.
        value: the monetary value the bidder assigns to this bundle.
        bid_id: optional unique identifier for the bid.
    """

    bidder_id: str
    bundle: frozenset[str]
    value: float
    bid_id: str | None = None

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"Bid value must be non-negative, got {self.value}")
        if len(self.bundle) == 0:
            raise ValueError("Bid bundle must contain at least one item")

    def __repr__(self) -> str:
        items = ", ".join(sorted(self.bundle))
        return f"Bid(bidder={self.bidder_id!r}, {{{items}}}, v={self.value:.2f})"


@dataclass
class Bidder:
    """A participant in the auction.

    A bidder submits one or more bids. The valuation function maps bundles
    (frozensets of item names) to values.

    Attributes:
        bidder_id: unique identifier for this bidder.
        bids: list of Bid objects submitted by this bidder.
    """

    bidder_id: str
    bids: list[Bid] = field(default_factory=list)

    def add_bid(self, bundle: frozenset[str], value: float) -> Bid:
        """Create and register a bid for the given bundle and value."""
        bid = Bid(
            bidder_id=self.bidder_id,
            bundle=bundle,
            value=value,
            bid_id=f"{self.bidder_id}_bid_{len(self.bids)}",
        )
        self.bids.append(bid)
        return bid

    def valuation(self, bundle: frozenset[str]) -> float:
        """Return the maximum value this bidder assigns to a bundle.

        Under XOR semantics the bidder can win at most one bid, so the
        valuation is the maximum value among bids whose bundle is a subset
        of the queried bundle.
        """
        best = 0.0
        for bid in self.bids:
            if bid.bundle.issubset(bundle):
                best = max(best, bid.value)
        return best

    def __repr__(self) -> str:
        return f"Bidder({self.bidder_id!r}, {len(self.bids)} bids)"


@dataclass
class Auction:
    """A combinatorial auction instance.

    Attributes:
        items: set of item names available in the auction.
        bidders: mapping from bidder_id to Bidder objects.
    """

    items: set[str] = field(default_factory=set)
    bidders: dict[str, Bidder] = field(default_factory=dict)

    def add_item(self, name: str) -> None:
        """Register an item in the auction."""
        self.items.add(name)

    def add_bidder(self, bidder_id: str) -> Bidder:
        """Create and register a new bidder."""
        if bidder_id in self.bidders:
            raise ValueError(f"Bidder {bidder_id!r} already exists")
        bidder = Bidder(bidder_id=bidder_id)
        self.bidders[bidder_id] = bidder
        return bidder

    def all_bids(self) -> list[Bid]:
        """Return a flat list of every bid across all bidders."""
        bids: list[Bid] = []
        for bidder in self.bidders.values():
            bids.extend(bidder.bids)
        return bids

    def validate(self) -> None:
        """Check that every bid references only known items."""
        for bid in self.all_bids():
            unknown = bid.bundle - self.items
            if unknown:
                raise ValueError(
                    f"Bid {bid} references unknown items: {unknown}"
                )

    def __repr__(self) -> str:
        return (
            f"Auction({len(self.items)} items, "
            f"{len(self.bidders)} bidders, "
            f"{len(self.all_bids())} bids)"
        )


@dataclass
class AllocationResult:
    """Result of solving the Winner Determination Problem.

    Attributes:
        winning_bids: list of accepted Bid objects.
        total_value: sum of values of winning bids (social welfare).
        item_assignment: mapping from item name to the bidder_id that wins it.
        solver_status: status string from the ILP solver.
    """

    winning_bids: list[Bid]
    total_value: float
    item_assignment: dict[str, str]
    solver_status: str

    @property
    def winner_ids(self) -> set[str]:
        """Set of bidder IDs that won at least one bid."""
        return {b.bidder_id for b in self.winning_bids}

    def bidder_bundle(self, bidder_id: str) -> frozenset[str]:
        """Return the union of items won by a specific bidder."""
        items: set[str] = set()
        for bid in self.winning_bids:
            if bid.bidder_id == bidder_id:
                items.update(bid.bundle)
        return frozenset(items)

    def bidder_value(self, bidder_id: str) -> float:
        """Return the total value of bids won by a specific bidder."""
        return sum(b.value for b in self.winning_bids if b.bidder_id == bidder_id)

    def __repr__(self) -> str:
        winners = ", ".join(sorted(self.winner_ids))
        return (
            f"AllocationResult(welfare={self.total_value:.2f}, "
            f"winners=[{winners}], status={self.solver_status!r})"
        )
