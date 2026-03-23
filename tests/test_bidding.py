"""Tests for bidding language implementations."""

from __future__ import annotations

from src.core.auction import Auction, Bidder
from src.core.bidding import (
    AdditiveORBid,
    BundleBid,
    ORBid,
    XORBid,
    apply_bidding_language,
)
from src.core.wdp import solve_wdp


class TestBundleBid:
    def test_single_bundle(self):
        bb = BundleBid("b1", frozenset(["A", "B"]), 10.0)
        bids = bb.to_bids()
        assert len(bids) == 1
        assert bids[0].bundle == frozenset(["A", "B"])
        assert bids[0].value == 10.0
        assert bids[0].bidder_id == "b1"


class TestXORBid:
    def test_xor_generates_dummy_item(self):
        xor = XORBid("b1")
        xor.add(frozenset(["A"]), 5.0)
        xor.add(frozenset(["B"]), 8.0)
        bids = xor.to_bids()

        assert len(bids) == 2
        # Each bid should contain a dummy item
        dummy = xor.dummy_items()
        for bid in bids:
            assert bid.bundle & dummy

    def test_xor_at_most_one_wins(self):
        """XOR semantics: at most one bid from the XOR group can win."""
        auction = Auction(items={"A", "B"})
        # Add the dummy item to auction items
        xor = XORBid("b1")
        xor.add(frozenset(["A"]), 5.0)
        xor.add(frozenset(["B"]), 8.0)

        auction.items.update(xor.dummy_items())
        bidder = auction.add_bidder("b1")
        apply_bidding_language(bidder, xor)

        result = solve_wdp(auction)
        # At most one bid from b1 should win
        b1_wins = [b for b in result.winning_bids if b.bidder_id == "b1"]
        assert len(b1_wins) <= 1

    def test_xor_best_bid_wins(self):
        """With no competition, the highest XOR bid should win."""
        auction = Auction(items={"A", "B"})
        xor = XORBid("b1")
        xor.add(frozenset(["A"]), 5.0)
        xor.add(frozenset(["B"]), 8.0)

        auction.items.update(xor.dummy_items())
        bidder = auction.add_bidder("b1")
        apply_bidding_language(bidder, xor)

        result = solve_wdp(auction)
        assert result.total_value == 8.0


class TestORBid:
    def test_or_no_transformation(self):
        """OR bids should produce bids without modification."""
        or_bid = ORBid("b1")
        or_bid.add(frozenset(["A"]), 5.0)
        or_bid.add(frozenset(["B"]), 3.0)

        bids = or_bid.to_bids()
        assert len(bids) == 2
        # No dummy items
        for bid in bids:
            assert "__" not in str(bid.bundle)

    def test_or_both_can_win(self):
        """OR semantics: both non-overlapping bids can win."""
        auction = Auction(items={"A", "B"})
        or_bid = ORBid("b1")
        or_bid.add(frozenset(["A"]), 5.0)
        or_bid.add(frozenset(["B"]), 3.0)

        bidder = auction.add_bidder("b1")
        apply_bidding_language(bidder, or_bid)

        result = solve_wdp(auction)
        assert result.total_value == 8.0

    def test_or_overlap_prevents_both(self):
        """Overlapping OR bids cannot both win."""
        auction = Auction(items={"A", "B"})
        or_bid = ORBid("b1")
        or_bid.add(frozenset(["A", "B"]), 10.0)
        or_bid.add(frozenset(["A"]), 5.0)

        bidder = auction.add_bidder("b1")
        apply_bidding_language(bidder, or_bid)

        result = solve_wdp(auction)
        # Can only win {A,B}=10 or {A}=5, not both (overlap on A)
        assert result.total_value == 10.0


class TestAdditiveORBid:
    def test_additive_generates_single_item_bids(self):
        aor = AdditiveORBid("b1")
        aor.add("A", 5.0)
        aor.add("B", 3.0)
        aor.add("C", 7.0)

        bids = aor.to_bids()
        assert len(bids) == 3
        for bid in bids:
            assert len(bid.bundle) == 1

    def test_additive_total_value(self):
        """All single-item bids can win simultaneously."""
        auction = Auction(items={"A", "B", "C"})
        aor = AdditiveORBid("b1")
        aor.add("A", 5.0)
        aor.add("B", 3.0)
        aor.add("C", 7.0)

        bidder = auction.add_bidder("b1")
        apply_bidding_language(bidder, aor)

        result = solve_wdp(auction)
        assert result.total_value == 15.0


class TestApplyBiddingLanguage:
    def test_apply_populates_bidder(self):
        bidder = Bidder(bidder_id="b1")
        bb = BundleBid("b1", frozenset(["X"]), 42.0)
        apply_bidding_language(bidder, bb)
        assert len(bidder.bids) == 1
        assert bidder.bids[0].value == 42.0

    def test_apply_multiple_languages(self):
        bidder = Bidder(bidder_id="b1")
        bb1 = BundleBid("b1", frozenset(["X"]), 10.0)
        bb2 = BundleBid("b1", frozenset(["Y"]), 20.0)
        apply_bidding_language(bidder, bb1)
        apply_bidding_language(bidder, bb2)
        assert len(bidder.bids) == 2


class TestBiddingIntegration:
    def test_xor_vs_or_different_outcomes(self):
        """XOR and OR should produce different allocations when both
        bids of a bidder are non-overlapping."""
        items = {"A", "B"}

        # OR: both can win -> total = 5 + 3 = 8
        auction_or = Auction(items=items.copy())
        or_bid = ORBid("b1")
        or_bid.add(frozenset(["A"]), 5.0)
        or_bid.add(frozenset(["B"]), 3.0)
        bidder_or = auction_or.add_bidder("b1")
        apply_bidding_language(bidder_or, or_bid)
        result_or = solve_wdp(auction_or)

        # XOR: only one can win -> total = 5
        auction_xor = Auction(items=items.copy())
        xor_bid = XORBid("b1")
        xor_bid.add(frozenset(["A"]), 5.0)
        xor_bid.add(frozenset(["B"]), 3.0)
        auction_xor.items.update(xor_bid.dummy_items())
        bidder_xor = auction_xor.add_bidder("b1")
        apply_bidding_language(bidder_xor, xor_bid)
        result_xor = solve_wdp(auction_xor)

        assert result_or.total_value == 8.0
        assert result_xor.total_value == 5.0
