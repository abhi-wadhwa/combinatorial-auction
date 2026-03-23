"""Winner Determination Problem (WDP) solver.

The WDP is a weighted set-packing problem: select a subset of bids that
maximises total value while ensuring no item is allocated more than once.

Formulation (ILP):
    maximise   sum_j  v_j * x_j
    subject to sum_{j : i in S_j} x_j  <=  1   for every item i
               x_j in {0, 1}                    for every bid j

We use PuLP with the bundled CBC solver.
"""

from __future__ import annotations

import pulp

from src.core.auction import AllocationResult, Auction, Bid


def solve_wdp(
    auction: Auction,
    exclude_bidder: str | None = None,
    fixed_bids: list[Bid] | None = None,
) -> AllocationResult:
    """Solve the Winner Determination Problem for the given auction.

    Args:
        auction: the auction instance containing items and bids.
        exclude_bidder: if set, remove all bids from this bidder before
            solving.  Used by the VCG payment computation.
        fixed_bids: if provided, use this list of bids instead of
            auction.all_bids().  Useful for custom bidding-language
            expansions.

    Returns:
        An AllocationResult with the optimal allocation.
    """
    bids = fixed_bids if fixed_bids is not None else auction.all_bids()

    # Filter out excluded bidder
    if exclude_bidder is not None:
        bids = [b for b in bids if b.bidder_id != exclude_bidder]

    if not bids:
        return AllocationResult(
            winning_bids=[],
            total_value=0.0,
            item_assignment={},
            solver_status="Optimal",
        )

    # Build item-to-bid index
    items_in_auction: set[str] = auction.items
    item_to_bids: dict[str, list[int]] = {item: [] for item in items_in_auction}
    for idx, bid in enumerate(bids):
        for item in bid.bundle:
            if item in item_to_bids:
                item_to_bids[item].append(idx)

    # Create ILP
    prob = pulp.LpProblem("WDP", pulp.LpMaximize)

    # Decision variables: x_j in {0, 1}
    x = [
        pulp.LpVariable(f"x_{j}", cat=pulp.LpBinary)
        for j in range(len(bids))
    ]

    # Objective: maximise sum(v_j * x_j)
    prob += pulp.lpSum(bids[j].value * x[j] for j in range(len(bids)))

    # Constraints: each item allocated at most once
    for item, bid_indices in item_to_bids.items():
        if bid_indices:
            prob += (
                pulp.lpSum(x[j] for j in bid_indices) <= 1,
                f"item_{item}",
            )

    # Solve (suppress solver output)
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    status = pulp.LpStatus[prob.status]

    winning_bids: list[Bid] = []
    item_assignment: dict[str, str] = {}

    if status == "Optimal":
        for j in range(len(bids)):
            if pulp.value(x[j]) is not None and pulp.value(x[j]) > 0.5:
                winning_bids.append(bids[j])
                for item in bids[j].bundle:
                    item_assignment[item] = bids[j].bidder_id

    total_value = sum(b.value for b in winning_bids)

    return AllocationResult(
        winning_bids=winning_bids,
        total_value=total_value,
        item_assignment=item_assignment,
        solver_status=status,
    )
