#!/usr/bin/env python3
"""End-to-end demo of the Combinatorial Auction Simulator.

Demonstrates:
  1. Manual auction setup with custom bids.
  2. Winner Determination via ILP.
  3. VCG payment computation.
  4. Core pricing check.
  5. Random auction generation.
"""

from __future__ import annotations

from src.core.auction import Auction
from src.core.vcg import compute_vcg_payments
from src.core.core_pricing import is_in_core, core_payment_bounds
from src.core.generators import generate_random_auction


def demo_manual_auction() -> None:
    """Run a hand-crafted spectrum auction example."""
    print("=" * 70)
    print("DEMO 1: Manual Spectrum Auction")
    print("=" * 70)
    print()

    # Auctioning two spectrum licences: East and West
    auction = Auction(items={"East", "West"})

    # National carrier wants both regions (complement valuations)
    national = auction.add_bidder("NationalCo")
    national.add_bid(frozenset(["East"]), 10.0)
    national.add_bid(frozenset(["West"]), 10.0)
    national.add_bid(frozenset(["East", "West"]), 25.0)  # synergy!

    # Eastern regional carrier
    eastern = auction.add_bidder("EastRegional")
    eastern.add_bid(frozenset(["East"]), 14.0)

    # Western regional carrier
    western = auction.add_bidder("WestRegional")
    western.add_bid(frozenset(["West"]), 12.0)

    print(f"Items: {sorted(auction.items)}")
    print(f"Bidders: {list(auction.bidders.keys())}")
    print()

    print("Bids:")
    for bid in auction.all_bids():
        bundle = "{" + ", ".join(sorted(bid.bundle)) + "}"
        print(f"  {bid.bidder_id}: {bundle} = ${bid.value:.0f}")
    print()

    # Solve
    vcg = compute_vcg_payments(auction)
    alloc = vcg.allocation

    print(f"Optimal social welfare: ${vcg.total_welfare:.0f}")
    print()

    print("Winning allocation:")
    for bid in alloc.winning_bids:
        bundle = "{" + ", ".join(sorted(bid.bundle)) + "}"
        print(f"  {bid.bidder_id} wins {bundle} (value=${bid.value:.0f})")
    print()

    print("VCG Payments:")
    for bidder_id in sorted(alloc.winner_ids):
        val = alloc.bidder_value(bidder_id)
        pay = vcg.payments[bidder_id]
        surplus = val - pay
        print(f"  {bidder_id}: pays ${pay:.0f} (value=${val:.0f}, surplus=${surplus:.0f})")

    print(f"\nTotal VCG revenue:  ${vcg.revenue:.0f}")
    print(f"First-price revenue: ${vcg.first_price_revenue():.0f}")
    print()

    # Core check
    core = is_in_core(auction, alloc, vcg.payments)
    if core.is_core:
        print("VCG payments are IN the core.")
    else:
        print("VCG payments are NOT in the core!")
        for coalition, deficit in core.violated_coalitions:
            print(f"  Blocking coalition {sorted(coalition)}: deficit=${deficit:.0f}")

    bounds = core_payment_bounds(auction, alloc)
    print("\nCore payment bounds:")
    for bidder_id, (lo, hi) in sorted(bounds.items()):
        print(f"  {bidder_id}: [${lo:.0f}, ${hi:.0f}]")
    print()


def demo_threshold_problem() -> None:
    """Demonstrate the threshold problem where VCG leaves the core."""
    print("=" * 70)
    print("DEMO 2: The Threshold Problem (VCG Outside Core)")
    print("=" * 70)
    print()

    auction = Auction(items={"A", "B"})

    # Two local bidders
    local_a = auction.add_bidder("Local_A")
    local_a.add_bid(frozenset(["A"]), 6.0)

    local_b = auction.add_bidder("Local_B")
    local_b.add_bid(frozenset(["B"]), 6.0)

    # One global bidder
    global_bid = auction.add_bidder("Global")
    global_bid.add_bid(frozenset(["A", "B"]), 10.0)

    vcg = compute_vcg_payments(auction)
    alloc = vcg.allocation

    print(f"Items: A, B")
    print(f"Local_A bids: {{A}} = $6")
    print(f"Local_B bids: {{B}} = $6")
    print(f"Global  bids: {{A,B}} = $10")
    print()
    print(f"Optimal: Local_A + Local_B = $12 > Global = $10")
    print()

    print("VCG payments:")
    for bidder_id in sorted(alloc.winner_ids):
        print(f"  {bidder_id}: pays ${vcg.payments[bidder_id]:.0f}")
    print(f"  Total revenue: ${vcg.revenue:.0f}")
    print()

    core = is_in_core(auction, alloc, vcg.payments)
    if not core.is_core:
        print("VCG payments violate the core!")
        print("The auctioneer could earn $10 from Global alone,")
        print(f"but VCG revenue is only ${vcg.revenue:.0f}.")
        for coalition, deficit in core.violated_coalitions:
            print(f"  Blocking coalition {sorted(coalition)}: deficit=${deficit:.2f}")
    print()


def demo_random_auction() -> None:
    """Generate and solve a random auction."""
    print("=" * 70)
    print("DEMO 3: Random Auction (5 items, 4 bidders)")
    print("=" * 70)
    print()

    auction = generate_random_auction(n_items=5, n_bidders=4, seed=42)

    print(f"Items: {sorted(auction.items)}")
    print(f"Bidders: {list(auction.bidders.keys())}")
    print(f"Total bids: {len(auction.all_bids())}")
    print()

    vcg = compute_vcg_payments(auction)
    alloc = vcg.allocation

    print(f"Social welfare: ${vcg.total_welfare:.2f}")
    print(f"VCG revenue:    ${vcg.revenue:.2f}")
    print(f"FP revenue:     ${vcg.first_price_revenue():.2f}")
    print()

    print("Winners:")
    for bidder_id in sorted(alloc.winner_ids):
        bundle = ", ".join(sorted(alloc.bidder_bundle(bidder_id)))
        val = alloc.bidder_value(bidder_id)
        pay = vcg.payments.get(bidder_id, 0)
        print(f"  {bidder_id}: {{{bundle}}} value=${val:.2f} pay=${pay:.2f}")
    print()

    core = is_in_core(
        auction, alloc, vcg.payments,
        max_coalition_size=min(len(auction.bidders), 4),
    )
    print(f"In core: {core.is_core}")
    print()


if __name__ == "__main__":
    demo_manual_auction()
    print()
    demo_threshold_problem()
    print()
    demo_random_auction()
