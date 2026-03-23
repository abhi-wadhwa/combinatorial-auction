"""Command-line interface for the Combinatorial Auction Simulator.

Usage:
    python -m src.cli demo           Run a built-in demo auction
    python -m src.cli random         Generate and solve a random auction
    python -m src.cli streamlit      Launch the Streamlit UI
"""

from __future__ import annotations

import argparse
import sys

from src.core.auction import Auction
from src.core.core_pricing import is_in_core
from src.core.generators import generate_random_auction
from src.core.vcg import compute_vcg_payments


def _print_results(auction: Auction) -> None:
    """Solve and print results for the given auction."""
    vcg = compute_vcg_payments(auction)
    alloc = vcg.allocation

    print("=" * 60)
    print("AUCTION INSTANCE")
    print("=" * 60)
    print(f"Items: {sorted(auction.items)}")
    print(f"Bidders: {list(auction.bidders.keys())}")
    print(f"Total bids: {len(auction.all_bids())}")
    print()

    print("All bids:")
    for bid in auction.all_bids():
        bundle_str = "{" + ", ".join(sorted(bid.bundle)) + "}"
        print(f"  {bid.bidder_id}: {bundle_str} -> {bid.value:.2f}")
    print()

    print("=" * 60)
    print("ALLOCATION (Winner Determination)")
    print("=" * 60)
    print(f"Solver status: {alloc.solver_status}")
    print(f"Social welfare: {alloc.total_value:.2f}")
    print()

    print("Winning bids:")
    for bid in alloc.winning_bids:
        bundle_str = "{" + ", ".join(sorted(bid.bundle)) + "}"
        print(f"  {bid.bidder_id}: {bundle_str} -> {bid.value:.2f}")
    print()

    print("Item assignment:")
    for item in sorted(auction.items):
        owner = alloc.item_assignment.get(item, "(unallocated)")
        print(f"  {item} -> {owner}")
    print()

    print("=" * 60)
    print("PAYMENTS")
    print("=" * 60)

    fp = vcg.first_price_payments()
    surplus = vcg.bidder_surplus()

    print(f"{'Bidder':<15} {'Value':>8} {'VCG Pay':>8} {'FP Pay':>8} {'Surplus':>8}")
    print("-" * 55)
    for bidder_id in sorted(alloc.winner_ids):
        val = alloc.bidder_value(bidder_id)
        vcg_p = vcg.payments.get(bidder_id, 0)
        fp_p = fp.get(bidder_id, 0)
        sur = surplus.get(bidder_id, 0)
        print(f"  {bidder_id:<13} {val:>8.2f} {vcg_p:>8.2f} {fp_p:>8.2f} {sur:>8.2f}")
    print()
    print(f"VCG Revenue:        {vcg.revenue:.2f}")
    print(f"First-Price Revenue: {vcg.first_price_revenue():.2f}")
    print()

    # Core check
    core = is_in_core(
        auction,
        alloc,
        vcg.payments,
        max_coalition_size=min(len(auction.bidders), 6),
    )
    print("=" * 60)
    print("CORE PRICING CHECK")
    print("=" * 60)
    if core.is_core:
        print("VCG payments ARE in the core.")
    else:
        print("VCG payments are NOT in the core.")
        print(f"Violated coalitions ({len(core.violated_coalitions)}):")
        for coalition, deficit in core.violated_coalitions[:10]:
            print(f"  {sorted(coalition)}: deficit = {deficit:.2f}")
    print()


def cmd_demo(_args: argparse.Namespace) -> None:
    """Run the built-in demo auction."""
    auction = Auction(items={"A", "B", "C"})

    b1 = auction.add_bidder("Alice")
    b1.add_bid(frozenset(["A", "B"]), 10.0)
    b1.add_bid(frozenset(["A"]), 5.0)

    b2 = auction.add_bidder("Bob")
    b2.add_bid(frozenset(["B", "C"]), 12.0)
    b2.add_bid(frozenset(["C"]), 4.0)

    b3 = auction.add_bidder("Charlie")
    b3.add_bid(frozenset(["A", "B", "C"]), 15.0)
    b3.add_bid(frozenset(["A"]), 6.0)
    b3.add_bid(frozenset(["B"]), 7.0)

    _print_results(auction)


def cmd_random(args: argparse.Namespace) -> None:
    """Generate and solve a random auction."""
    auction = generate_random_auction(
        n_items=args.items,
        n_bidders=args.bidders,
        seed=args.seed,
    )
    _print_results(auction)


def cmd_streamlit(_args: argparse.Namespace) -> None:
    """Launch the Streamlit app."""
    import subprocess
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "src/viz/app.py"],
        check=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Combinatorial Auction Simulator",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("demo", help="Run the built-in demo auction")

    rand_p = sub.add_parser("random", help="Generate and solve a random auction")
    rand_p.add_argument("--items", type=int, default=5, help="Number of items")
    rand_p.add_argument("--bidders", type=int, default=4, help="Number of bidders")
    rand_p.add_argument("--seed", type=int, default=42, help="Random seed")

    sub.add_parser("streamlit", help="Launch the Streamlit UI")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "demo": cmd_demo,
        "random": cmd_random,
        "streamlit": cmd_streamlit,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
