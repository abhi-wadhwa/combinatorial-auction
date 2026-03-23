"""Core pricing check for combinatorial auctions.

The *core* of a combinatorial auction is the set of payment vectors
(p_1, ..., p_n) such that:

    1. Individual rationality (IR): p_i <= v_i(S_i*) for every winner i.
    2. No blocking coalition: for every subset S of bidders,
           sum_{all winners} p_i  >=  V*(S)
       That is, the total revenue must be at least as large as the welfare
       achievable by re-allocating to any subset S of bidders.

Equivalently (and more practically for per-bidder bounds), the core
constraint for a complementary coalition S (those NOT in S) is:

    sum_{i in S_bar} (v_i(S_i*) - p_i) <= V*(N) - V*(S)

where S_bar = N \\ S are the bidders not in the blocking coalition.

VCG payments are not always in the core (a well-known issue in
combinatorial auctions with complementarities).  This module checks
whether the VCG payment vector lies in the core and computes
per-bidder core payment bounds.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from src.core.auction import AllocationResult, Auction, Bid
from src.core.wdp import solve_wdp


@dataclass
class CoreCheckResult:
    """Result of checking whether a payment vector is in the core.

    Attributes:
        is_core: True if the payments are in the core.
        violated_coalitions: list of (coalition, deficit) pairs for
            coalitions whose core constraint is violated.
        payment_bounds: per-bidder (lower, upper) bounds implied by the
            core constraints, where lower is the tightest blocking
            constraint and upper is the IR constraint.
    """

    is_core: bool
    violated_coalitions: list[tuple[set[str], float]]
    payment_bounds: dict[str, tuple[float, float]]

    def __repr__(self) -> str:
        if self.is_core:
            return "CoreCheckResult(in_core=True)"
        n_viol = len(self.violated_coalitions)
        return f"CoreCheckResult(in_core=False, {n_viol} violated coalitions)"


def _coalition_value(auction: Auction, coalition: set[str]) -> float:
    """Compute V*(C): optimal welfare achievable by a coalition C."""
    coalition_bids: list[Bid] = []
    for bidder_id in coalition:
        if bidder_id in auction.bidders:
            coalition_bids.extend(auction.bidders[bidder_id].bids)

    if not coalition_bids:
        return 0.0

    result = solve_wdp(auction, fixed_bids=coalition_bids)
    return result.total_value


def is_in_core(
    auction: Auction,
    allocation: AllocationResult,
    payments: dict[str, float],
    max_coalition_size: int = 0,
) -> CoreCheckResult:
    """Check whether the given payments lie in the core.

    The core constraint is: for every subset S of bidders,
        total_revenue >= V*(S)

    For computational tractability, you can limit the maximum coalition
    size to check.  Setting max_coalition_size=0 (default) checks all
    possible coalitions (exponential in number of bidders).

    Args:
        auction: the auction instance.
        allocation: the optimal allocation.
        payments: mapping bidder_id -> payment amount.
        max_coalition_size: largest coalition to enumerate (0 = all).

    Returns:
        A CoreCheckResult.
    """
    bidder_ids = list(auction.bidders.keys())
    n = len(bidder_ids)
    total_welfare = allocation.total_value

    if max_coalition_size <= 0:
        max_coalition_size = n

    # Total revenue from all winners
    total_revenue = sum(payments.get(b, 0.0) for b in bidder_ids)

    violated: list[tuple[set[str], float]] = []
    payment_lower: dict[str, float] = {bid_id: 0.0 for bid_id in bidder_ids}
    payment_upper: dict[str, float] = {}

    # Upper bound (IR): p_i <= v_i(S_i*)
    for bidder_id in bidder_ids:
        val = allocation.bidder_value(bidder_id)
        payment_upper[bidder_id] = val

    # Check coalition constraints.
    # For each subset S: total_revenue >= V*(S).
    # Equivalently, for singleton {i} as the complement (S = N\{i}):
    #   total_revenue >= V*(N\{i})
    # And for the per-bidder lower bound from the singleton blocking
    # constraint where S = {i}: total_revenue >= V*({i}).
    #
    # The per-bidder constraint can be derived from the complement view.
    # If S_bar = {i} (only bidder i is NOT in the blocking coalition):
    #   v_i - p_i <= V*(N) - V*(N\{i})
    #   p_i >= v_i - V*(N) + V*(N\{i})
    # This is exactly the VCG payment!
    #
    # For the general coalition S (blocking coalition), the constraint is
    # on total revenue, not individual payments. We check:
    #   total_revenue >= V*(S)

    for size in range(1, max_coalition_size + 1):
        for coalition_tuple in combinations(bidder_ids, size):
            coalition = set(coalition_tuple)

            # Compute V*(S): optimal welfare using only bidders in S
            v_star_s = _coalition_value(auction, coalition)

            # Core constraint: total revenue >= V*(S)
            if total_revenue < v_star_s - 1e-9:
                deficit = v_star_s - total_revenue
                violated.append((coalition, deficit))

            # For singleton S={i}, derive per-bidder lower bound.
            # From the complement view (S_bar = N\{i}):
            #   sum_{j != i} (v_j - p_j) <= V*(N) - V*({i})
            # Rearranging: sum_{j != i} p_j >= sum_{j != i} v_j - V*(N) + V*({i})
            # Since sum_all p_j = sum_{j != i} p_j + p_i, and we need
            # total_revenue >= V*({i}), but this doesn't directly give us
            # a per-bidder bound from singleton S.
            #
            # The meaningful per-bidder lower bound comes from considering
            # the "complement" coalition. For bidder i, the tightest lower
            # bound comes from the constraint where S = N\{i}:
            #   p_i >= v_i - V*(N) + V*(N\{i})
            # This is the VCG payment itself.

    # Compute per-bidder lower bounds from complement coalitions
    # For each bidder i: p_i >= v_i(S_i*) - V*(N) + V*(N\{i})
    for bidder_id in bidder_ids:
        v_i = allocation.bidder_value(bidder_id)
        if v_i > 0:
            # V*(N\{i})
            complement = set(bidder_ids) - {bidder_id}
            v_without_i = _coalition_value(auction, complement) if complement else 0.0
            # Lower bound = v_i - V*(N) + V*(N\{i})
            lb = v_i - total_welfare + v_without_i
            payment_lower[bidder_id] = max(payment_lower[bidder_id], lb)

    # Build bounds dict
    bounds: dict[str, tuple[float, float]] = {}
    for bid_id in bidder_ids:
        lo = max(payment_lower.get(bid_id, 0.0), 0.0)
        hi = payment_upper.get(bid_id, 0.0)
        bounds[bid_id] = (lo, hi)

    return CoreCheckResult(
        is_core=len(violated) == 0,
        violated_coalitions=violated,
        payment_bounds=bounds,
    )


def core_payment_bounds(
    auction: Auction,
    allocation: AllocationResult,
    max_coalition_size: int = 0,
) -> dict[str, tuple[float, float]]:
    """Compute per-bidder (lower, upper) core payment bounds.

    The lower bound for bidder i is derived from the constraint:
        p_i >= v_i(S_i*) - V*(N) + V*(N \\ {i})
    which equals the VCG payment.

    The upper bound is the individual-rationality constraint:
        p_i <= v_i(S_i*)

    Args:
        auction: the auction instance.
        allocation: the optimal allocation.
        max_coalition_size: largest coalition to enumerate (0 = all).

    Returns:
        Dict mapping bidder_id to (min_core_payment, max_core_payment).
    """
    bidder_ids = list(auction.bidders.keys())
    total_welfare = allocation.total_value

    lower: dict[str, float] = {b: 0.0 for b in bidder_ids}
    upper: dict[str, float] = {}

    for bidder_id in bidder_ids:
        upper[bidder_id] = allocation.bidder_value(bidder_id)

    # Per-bidder lower bound from complement constraint
    for bidder_id in bidder_ids:
        v_i = allocation.bidder_value(bidder_id)
        if v_i > 0:
            complement = set(bidder_ids) - {bidder_id}
            v_without_i = _coalition_value(auction, complement) if complement else 0.0
            lb = v_i - total_welfare + v_without_i
            lower[bidder_id] = max(lower[bidder_id], lb)

    bounds: dict[str, tuple[float, float]] = {}
    for bid_id in bidder_ids:
        lo = max(lower.get(bid_id, 0.0), 0.0)
        hi = max(upper.get(bid_id, 0.0), 0.0)
        bounds[bid_id] = (lo, hi)

    return bounds
