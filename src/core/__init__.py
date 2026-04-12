"""Core auction engine: WDP solver, VCG payments, core pricing, bidding languages."""

from src.core.auction import AllocationResult, Auction, Bid, Bidder, Item
from src.core.bidding import AdditiveORBid, BundleBid, ORBid, XORBid
from src.core.core_pricing import core_payment_bounds, is_in_core
from src.core.generators import (
    generate_additive_bidder,
    generate_complements_bidder,
    generate_random_auction,
    generate_single_minded_bidder,
    generate_substitutes_bidder,
)
from src.core.vcg import compute_vcg_payments
from src.core.wdp import solve_wdp

__all__ = [
    "Item",
    "Bid",
    "Bidder",
    "Auction",
    "AllocationResult",
    "solve_wdp",
    "compute_vcg_payments",
    "is_in_core",
    "core_payment_bounds",
    "XORBid",
    "ORBid",
    "AdditiveORBid",
    "BundleBid",
    "generate_additive_bidder",
    "generate_substitutes_bidder",
    "generate_complements_bidder",
    "generate_single_minded_bidder",
    "generate_random_auction",
]
