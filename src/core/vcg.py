"""Vickrey-Clarke-Groves (VCG) payment computation.

The VCG mechanism charges each winning bidder the externality they impose
on the other participants.  For bidder i who wins bundle S_i* with value
v_i(S_i*):

    p_i  =  V*(N \\ {i})  -  [ V*(N) - v_i(S_i*) ]

where V*(N) is the optimal social welfare with all bidders, and V*(N\\{i})
is the optimal welfare when bidder i is excluded.

This requires solving n+1 ILPs: one with all bidders and one per winning
bidder with that bidder excluded.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.auction import AllocationResult, Auction
from src.core.wdp import solve_wdp


@dataclass
class VCGResult:
    """Container for VCG mechanism outputs.

    Attributes:
        allocation: the welfare-maximising allocation.
        payments: mapping from bidder_id to VCG payment.
        welfare_without: mapping from bidder_id to V*(N\\{i}).
        total_welfare: V*(N), the optimal social welfare.
        revenue: sum of all VCG payments (auctioneer revenue).
    """

    allocation: AllocationResult
    payments: dict[str, float]
    welfare_without: dict[str, float]
    total_welfare: float

    @property
    def revenue(self) -> float:
        return sum(self.payments.values())

    def first_price_payments(self) -> dict[str, float]:
        """Return first-price (pay-your-bid) payments for comparison."""
        fp: dict[str, float] = {}
        for bid in self.allocation.winning_bids:
            fp[bid.bidder_id] = fp.get(bid.bidder_id, 0.0) + bid.value
        return fp

    def first_price_revenue(self) -> float:
        return sum(self.first_price_payments().values())

    def bidder_surplus(self) -> dict[str, float]:
        """Return each winner's surplus (value minus VCG payment)."""
        surplus: dict[str, float] = {}
        for bidder_id in self.allocation.winner_ids:
            value = self.allocation.bidder_value(bidder_id)
            surplus[bidder_id] = value - self.payments.get(bidder_id, 0.0)
        return surplus

    def efficiency(self) -> float:
        """Return allocative efficiency (always 1.0 for VCG by construction)."""
        return 1.0 if self.total_welfare > 0 else 0.0

    def __repr__(self) -> str:
        return (
            f"VCGResult(welfare={self.total_welfare:.2f}, "
            f"revenue={self.revenue:.2f}, "
            f"payments={self.payments})"
        )


def compute_vcg_payments(auction: Auction) -> VCGResult:
    """Run the full VCG mechanism on the given auction.

    Steps:
        1. Solve WDP with all bidders  ->  V*(N), allocation.
        2. For each winning bidder i, solve WDP excluding i  ->  V*(N\\{i}).
        3. Compute p_i = V*(N\\{i}) - (V*(N) - v_i(S_i*)).

    Returns:
        A VCGResult with allocation and payment details.
    """
    # Step 1: solve with all bidders
    allocation = solve_wdp(auction)
    total_welfare = allocation.total_value

    payments: dict[str, float] = {}
    welfare_without: dict[str, float] = {}

    # Step 2 & 3: for each winning bidder, compute externality
    for bidder_id in allocation.winner_ids:
        # Solve WDP excluding bidder i
        result_without = solve_wdp(auction, exclude_bidder=bidder_id)
        v_star_without_i = result_without.total_value
        welfare_without[bidder_id] = v_star_without_i

        # Value won by bidder i in the optimal allocation
        v_i = allocation.bidder_value(bidder_id)

        # VCG payment: externality imposed on others
        # p_i = V*(N\{i}) - (V*(N) - v_i)
        # Equivalently: p_i = V*(N\{i}) - sum of other winners' values
        payment = v_star_without_i - (total_welfare - v_i)
        payments[bidder_id] = max(payment, 0.0)  # non-negative payments

    return VCGResult(
        allocation=allocation,
        payments=payments,
        welfare_without=welfare_without,
        total_welfare=total_welfare,
    )
