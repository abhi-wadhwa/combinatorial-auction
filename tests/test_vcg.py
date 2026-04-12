"""Tests for VCG payment computation."""

from __future__ import annotations

from src.core.auction import Auction
from src.core.vcg import compute_vcg_payments


def _three_bidder_auction() -> Auction:
    """Classic three-bidder auction with known VCG payments.

    Items: A, B
    Alice bids:   {A} = 10
    Bob bids:     {B} = 8
    Charlie bids: {A,B} = 12

    Optimal: Alice({A})=10 + Bob({B})=8 = 18
    V*(N\\Alice) = Charlie({A,B})=12  (Bob only bids on B=8, but Charlie
        can get {A,B}=12 which includes B, so max(Bob(B)=8, Charlie({A,B})=12) = 12)
    V*(N\\Bob) = max(Alice(A)=10, Charlie({A,B})=12) = 12
        (Alice and Charlie cannot both win because {A} and {A,B} overlap on A)

    p_Alice = V*(N\\Alice) - (V*(N) - v_Alice) = 12 - (18-10) = 12-8 = 4
    p_Bob   = V*(N\\Bob)   - (V*(N) - v_Bob)   = 12 - (18-8)  = 12-10 = 2
    """
    auction = Auction(items={"A", "B"})

    b1 = auction.add_bidder("Alice")
    b1.add_bid(frozenset(["A"]), 10.0)

    b2 = auction.add_bidder("Bob")
    b2.add_bid(frozenset(["B"]), 8.0)

    b3 = auction.add_bidder("Charlie")
    b3.add_bid(frozenset(["A", "B"]), 12.0)

    return auction


class TestVCGPayments:
    def test_known_instance(self):
        """Verify VCG payments on a known instance."""
        auction = _three_bidder_auction()
        vcg = compute_vcg_payments(auction)

        assert vcg.total_welfare == 18.0
        assert vcg.allocation.total_value == 18.0
        assert "Alice" in vcg.allocation.winner_ids
        assert "Bob" in vcg.allocation.winner_ids
        assert "Charlie" not in vcg.allocation.winner_ids

        assert abs(vcg.payments["Alice"] - 4.0) < 1e-6
        assert abs(vcg.payments["Bob"] - 2.0) < 1e-6

    def test_vcg_revenue(self):
        auction = _three_bidder_auction()
        vcg = compute_vcg_payments(auction)
        # Alice pays 4, Bob pays 2 -> revenue = 6
        assert abs(vcg.revenue - 6.0) < 1e-6

    def test_first_price_revenue(self):
        auction = _three_bidder_auction()
        vcg = compute_vcg_payments(auction)
        # First-price: Alice pays 10, Bob pays 8
        assert abs(vcg.first_price_revenue() - 18.0) < 1e-6


class TestVCGTruthfulness:
    """VCG is strategyproof: no bidder can gain by misreporting."""

    def test_alice_cannot_gain_by_overbidding(self):
        """If Alice bids higher, she still wins and pays the same."""
        # True auction
        auction_true = _three_bidder_auction()
        vcg_true = compute_vcg_payments(auction_true)
        alice_surplus_true = (
            vcg_true.allocation.bidder_value("Alice")
            - vcg_true.payments["Alice"]
        )

        # Alice overbids
        auction_over = Auction(items={"A", "B"})
        b1 = auction_over.add_bidder("Alice")
        b1.add_bid(frozenset(["A"]), 20.0)  # overbid
        b2 = auction_over.add_bidder("Bob")
        b2.add_bid(frozenset(["B"]), 8.0)
        b3 = auction_over.add_bidder("Charlie")
        b3.add_bid(frozenset(["A", "B"]), 12.0)

        vcg_over = compute_vcg_payments(auction_over)
        # Alice's TRUE surplus (based on real value 10, not bid 20)
        alice_true_val = 10.0  # her real value
        alice_surplus_over = alice_true_val - vcg_over.payments.get("Alice", 0)

        # Surplus should not improve
        assert alice_surplus_over <= alice_surplus_true + 1e-6

    def test_alice_cannot_gain_by_underbidding(self):
        """If Alice underbids to 3, Charlie wins {A,B} and Alice gets nothing."""
        auction_under = Auction(items={"A", "B"})
        b1 = auction_under.add_bidder("Alice")
        b1.add_bid(frozenset(["A"]), 3.0)  # underbid
        b2 = auction_under.add_bidder("Bob")
        b2.add_bid(frozenset(["B"]), 8.0)
        b3 = auction_under.add_bidder("Charlie")
        b3.add_bid(frozenset(["A", "B"]), 12.0)

        vcg_under = compute_vcg_payments(auction_under)
        # Charlie wins {A,B}=12 > Alice(A)=3 + Bob(B)=8 = 11
        assert vcg_under.total_welfare == 12.0
        assert "Charlie" in vcg_under.allocation.winner_ids
        # Alice gets nothing -> surplus = 0
        alice_surplus_under = 0.0

        # True auction surplus
        auction_true = _three_bidder_auction()
        vcg_true = compute_vcg_payments(auction_true)
        alice_surplus_true = (
            vcg_true.allocation.bidder_value("Alice")
            - vcg_true.payments["Alice"]
        )
        # Truthful surplus (10 - 4 = 6) >= underbid surplus (0)
        assert alice_surplus_true >= alice_surplus_under - 1e-6

    def test_no_bidder_gains_by_dropping_out(self):
        """Each winner's surplus under truthful VCG >= 0."""
        auction = _three_bidder_auction()
        vcg = compute_vcg_payments(auction)
        for bidder_id, surplus in vcg.bidder_surplus().items():
            assert surplus >= -1e-6, (
                f"Bidder {bidder_id} has negative surplus: {surplus}"
            )


class TestVCGNonNegativePayments:
    def test_payments_nonnegative(self):
        """VCG payments should always be non-negative."""
        auction = _three_bidder_auction()
        vcg = compute_vcg_payments(auction)
        for bidder_id, payment in vcg.payments.items():
            assert payment >= -1e-6, (
                f"Bidder {bidder_id} has negative payment: {payment}"
            )

    def test_payments_at_most_value(self):
        """VCG payment <= value won (individual rationality)."""
        auction = _three_bidder_auction()
        vcg = compute_vcg_payments(auction)
        for bidder_id in vcg.allocation.winner_ids:
            val = vcg.allocation.bidder_value(bidder_id)
            pay = vcg.payments.get(bidder_id, 0)
            assert pay <= val + 1e-6


class TestVCGEdgeCases:
    def test_single_bidder(self):
        """Single bidder pays 0 (no competition)."""
        auction = Auction(items={"A"})
        b = auction.add_bidder("solo")
        b.add_bid(frozenset(["A"]), 100.0)

        vcg = compute_vcg_payments(auction)
        assert vcg.total_welfare == 100.0
        assert abs(vcg.payments["solo"] - 0.0) < 1e-6

    def test_two_bidders_same_item(self):
        """Two bidders for one item: winner pays loser's value."""
        auction = Auction(items={"X"})
        b1 = auction.add_bidder("high")
        b1.add_bid(frozenset(["X"]), 20.0)
        b2 = auction.add_bidder("low")
        b2.add_bid(frozenset(["X"]), 12.0)

        vcg = compute_vcg_payments(auction)
        assert "high" in vcg.allocation.winner_ids
        # p_high = V*(N\{high}) - (V*(N) - v_high) = 12 - (20-20) = 12
        assert abs(vcg.payments["high"] - 12.0) < 1e-6

    def test_no_winners(self):
        """Empty auction has zero welfare and no payments."""
        auction = Auction(items={"A", "B"})
        vcg = compute_vcg_payments(auction)
        assert vcg.total_welfare == 0.0
        assert vcg.revenue == 0.0


class TestVCGKnownExample:
    """Textbook spectrum auction example under OR semantics."""

    def test_spectrum_auction_example(self):
        """
        Items: East, West
        Bidder A: {East}=10, {West}=10, {East,West}=12
        Bidder B: {East}=8
        Bidder C: {West}=6

        Under OR semantics, A can win both {East}=10 AND {West}=10 = 20.
        This beats any other combination:
          - A(East)+A(West) = 20
          - A(East)+B(East): conflict on East
          - A(West)+B(East) = 10+8 = 18
          - A({East,West}) = 12
          - B(East)+C(West) = 14

        So V*(N) = 20 (A wins both items with separate bids).

        V*(N\\A) = B(East)+C(West) = 14
        p_A = 14 - (20-20) = 14

        Total revenue = 14, first-price = 20.
        """
        auction = Auction(items={"East", "West"})
        a = auction.add_bidder("A")
        a.add_bid(frozenset(["East"]), 10.0)
        a.add_bid(frozenset(["West"]), 10.0)
        a.add_bid(frozenset(["East", "West"]), 12.0)

        b = auction.add_bidder("B")
        b.add_bid(frozenset(["East"]), 8.0)

        c = auction.add_bidder("C")
        c.add_bid(frozenset(["West"]), 6.0)

        vcg = compute_vcg_payments(auction)

        # Optimal: A wins East(10) + West(10) = 20
        assert vcg.total_welfare == 20.0
        assert "A" in vcg.allocation.winner_ids

        # VCG payment: A pays 14
        assert abs(vcg.payments["A"] - 14.0) < 1e-6

    def test_spectrum_with_competition(self):
        """A cleaner example with genuine multi-bidder competition.

        Items: East, West
        Bidder A: {East}=10
        Bidder B: {West}=8
        Bidder C: {East,West}=15

        Optimal: A(East)+B(West) = 18 > C({East,West})=15
        V*(N\\A) = C({East,West})=15 (beats B(West)=8)
        V*(N\\B) = C({East,West})=15 (beats A(East)=10)

        p_A = 15 - (18-10) = 15-8 = 7
        p_B = 15 - (18-8)  = 15-10 = 5
        """
        auction = Auction(items={"East", "West"})
        a = auction.add_bidder("A")
        a.add_bid(frozenset(["East"]), 10.0)

        b = auction.add_bidder("B")
        b.add_bid(frozenset(["West"]), 8.0)

        c = auction.add_bidder("C")
        c.add_bid(frozenset(["East", "West"]), 15.0)

        vcg = compute_vcg_payments(auction)
        assert vcg.total_welfare == 18.0
        assert "A" in vcg.allocation.winner_ids
        assert "B" in vcg.allocation.winner_ids

        assert abs(vcg.payments["A"] - 7.0) < 1e-6
        assert abs(vcg.payments["B"] - 5.0) < 1e-6
        assert abs(vcg.revenue - 12.0) < 1e-6
