"""Tests for the Winner Determination Problem solver."""

from __future__ import annotations

from src.core.auction import Auction
from src.core.wdp import solve_wdp


def _simple_auction() -> Auction:
    """Two bidders, three items, known optimal."""
    auction = Auction(items={"A", "B", "C"})
    b1 = auction.add_bidder("b1")
    b1.add_bid(frozenset(["A", "B"]), 10.0)

    b2 = auction.add_bidder("b2")
    b2.add_bid(frozenset(["B", "C"]), 8.0)

    b3 = auction.add_bidder("b3")
    b3.add_bid(frozenset(["C"]), 5.0)
    return auction


class TestWDPBasic:
    def test_optimal_value(self):
        """WDP should pick {A,B}=10 + {C}=5 = 15 over {B,C}=8."""
        auction = _simple_auction()
        result = solve_wdp(auction)
        assert result.solver_status == "Optimal"
        # b1 gets {A,B}=10, b3 gets {C}=5 -> total 15
        # Alternatively: b2 gets {B,C}=8 -> only 8
        assert result.total_value == 15.0

    def test_no_item_conflict(self):
        """No item should be assigned to more than one bidder."""
        auction = _simple_auction()
        result = solve_wdp(auction)
        seen_items = set()
        for bid in result.winning_bids:
            overlap = bid.bundle & seen_items
            assert len(overlap) == 0, f"Item conflict: {overlap}"
            seen_items.update(bid.bundle)

    def test_winners(self):
        auction = _simple_auction()
        result = solve_wdp(auction)
        assert "b1" in result.winner_ids
        assert "b3" in result.winner_ids
        assert "b2" not in result.winner_ids

    def test_item_assignment(self):
        auction = _simple_auction()
        result = solve_wdp(auction)
        assert result.item_assignment["A"] == "b1"
        assert result.item_assignment["B"] == "b1"
        assert result.item_assignment["C"] == "b3"


class TestWDPExclude:
    def test_exclude_bidder(self):
        """Excluding b1 should yield b2 winning {B,C}=8."""
        auction = _simple_auction()
        result = solve_wdp(auction, exclude_bidder="b1")
        assert "b1" not in result.winner_ids
        assert (
            result.total_value == 8.0
            or result.total_value >= 5.0
        )
        # Actually: b2 gets {B,C}=8, or b3 gets {C}=5.
        # b2({B,C})=8 > b3({C})=5, so optimal without b1 is b2=8 + nothing or b3=5
        # But b2({B,C})=8 alone is better, and b3({C})=5 conflicts with b2 on C
        # So: V*(N\{b1}) = 8
        assert result.total_value == 8.0

    def test_exclude_nonexistent(self):
        """Excluding a non-existent bidder should give full solution."""
        auction = _simple_auction()
        result = solve_wdp(auction, exclude_bidder="nobody")
        assert result.total_value == 15.0


class TestWDPEdgeCases:
    def test_empty_auction(self):
        auction = Auction(items={"A"})
        result = solve_wdp(auction)
        assert result.total_value == 0.0
        assert result.winning_bids == []

    def test_single_bid(self):
        auction = Auction(items={"X"})
        b = auction.add_bidder("only")
        b.add_bid(frozenset(["X"]), 42.0)
        result = solve_wdp(auction)
        assert result.total_value == 42.0

    def test_competing_bids_same_item(self):
        """Two bidders want the same single item."""
        auction = Auction(items={"X"})
        b1 = auction.add_bidder("b1")
        b1.add_bid(frozenset(["X"]), 10.0)
        b2 = auction.add_bidder("b2")
        b2.add_bid(frozenset(["X"]), 15.0)

        result = solve_wdp(auction)
        assert result.total_value == 15.0
        assert "b2" in result.winner_ids
        assert "b1" not in result.winner_ids

    def test_many_small_vs_one_large(self):
        """Three single-item bids (3+4+5=12) vs one bundle bid (10)."""
        auction = Auction(items={"A", "B", "C"})
        for i, (item, val) in enumerate([("A", 3), ("B", 4), ("C", 5)]):
            b = auction.add_bidder(f"small_{i}")
            b.add_bid(frozenset([item]), val)

        big = auction.add_bidder("big")
        big.add_bid(frozenset(["A", "B", "C"]), 10.0)

        result = solve_wdp(auction)
        # 3+4+5=12 > 10, so three small bidders win
        assert result.total_value == 12.0

    def test_large_bundle_wins(self):
        """One large bundle bid (20) vs three small (3+4+5=12)."""
        auction = Auction(items={"A", "B", "C"})
        for i, (item, val) in enumerate([("A", 3), ("B", 4), ("C", 5)]):
            b = auction.add_bidder(f"small_{i}")
            b.add_bid(frozenset([item]), val)

        big = auction.add_bidder("big")
        big.add_bid(frozenset(["A", "B", "C"]), 20.0)

        result = solve_wdp(auction)
        assert result.total_value == 20.0
        assert result.winner_ids == {"big"}


class TestWDPMaximizesValue:
    """Property: WDP always finds the welfare-maximising allocation."""

    def test_welfare_is_maximal(self):
        """Brute-force check: no feasible allocation has higher value."""
        auction = Auction(items={"A", "B", "C"})

        b1 = auction.add_bidder("b1")
        b1.add_bid(frozenset(["A"]), 5.0)
        b1.add_bid(frozenset(["A", "B"]), 8.0)

        b2 = auction.add_bidder("b2")
        b2.add_bid(frozenset(["B"]), 6.0)
        b2.add_bid(frozenset(["B", "C"]), 9.0)

        b3 = auction.add_bidder("b3")
        b3.add_bid(frozenset(["C"]), 4.0)
        b3.add_bid(frozenset(["A", "C"]), 7.0)

        result = solve_wdp(auction)

        # Enumerate all feasible allocations by brute force
        bids = auction.all_bids()
        best = 0.0
        for mask in range(1 << len(bids)):
            selected = [bids[j] for j in range(len(bids)) if mask & (1 << j)]
            # Check feasibility
            used_items = set()
            feasible = True
            for bid in selected:
                if bid.bundle & used_items:
                    feasible = False
                    break
                used_items.update(bid.bundle)
            if feasible:
                val = sum(b.value for b in selected)
                best = max(best, val)

        assert abs(result.total_value - best) < 1e-6
