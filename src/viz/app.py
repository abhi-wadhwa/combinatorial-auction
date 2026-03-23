"""Streamlit UI for the Combinatorial Auction Simulator.

Provides an interactive interface for:
  - Defining items and bidders with bundle valuations.
  - Running the WDP solver and VCG mechanism.
  - Visualising allocations, payments, and efficiency metrics.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.core.auction import Auction
from src.core.core_pricing import is_in_core
from src.core.generators import generate_random_auction
from src.core.vcg import compute_vcg_payments

# ── colour palette for bidder cards ──────────────────────────────────────
COLOURS = [
    "#4CAF50", "#2196F3", "#FF9800", "#9C27B0",
    "#F44336", "#00BCD4", "#8BC34A", "#FF5722",
    "#3F51B5", "#CDDC39", "#E91E63", "#009688",
]


def _colour(idx: int) -> str:
    return COLOURS[idx % len(COLOURS)]


# ── page config ──────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(
        page_title="Combinatorial Auction Simulator",
        page_icon="",
        layout="wide",
    )

    st.title("Combinatorial Auction Simulator")
    st.markdown(
        "Solve the **Winner Determination Problem** (ILP), compute "
        "**VCG payments**, and check **core pricing**."
    )

    # ── sidebar: auction setup ───────────────────────────────────────────
    with st.sidebar:
        st.header("Auction Setup")

        mode = st.radio(
            "Mode",
            ["Manual", "Random generator"],
            horizontal=True,
        )

        if mode == "Random generator":
            n_items = st.slider("Number of items", 2, 10, 4)
            n_bidders = st.slider("Number of bidders", 2, 8, 4)
            seed = st.number_input("Random seed", value=42, step=1)
            if st.button("Generate auction", use_container_width=True):
                auction = generate_random_auction(
                    n_items=n_items, n_bidders=n_bidders, seed=int(seed)
                )
                st.session_state["auction"] = auction
                st.session_state["results"] = None
        else:
            # Manual item entry
            items_str = st.text_input(
                "Items (comma-separated)",
                value="A, B, C, D",
            )
            items = [s.strip() for s in items_str.split(",") if s.strip()]

            st.subheader("Bidders")
            n_manual = st.number_input(
                "Number of bidders", min_value=1, max_value=20, value=3
            )

            auction = Auction(items=set(items))
            for i in range(int(n_manual)):
                bid_id = f"bidder_{i}"
                with st.expander(f"Bidder {i}", expanded=(i < 2)):
                    n_bids = st.number_input(
                        f"Number of bids for bidder {i}",
                        min_value=1,
                        max_value=20,
                        value=2,
                        key=f"nbids_{i}",
                    )
                    bidder = auction.add_bidder(bid_id)
                    for j in range(int(n_bids)):
                        cols = st.columns([3, 1])
                        with cols[0]:
                            bundle_str = st.text_input(
                                f"Bundle {j} items",
                                value=", ".join(items[: min(2, len(items))]),
                                key=f"bundle_{i}_{j}",
                            )
                        with cols[1]:
                            val = st.number_input(
                                "Value",
                                min_value=0.0,
                                value=10.0,
                                step=0.5,
                                key=f"val_{i}_{j}",
                            )
                        bundle_items = frozenset(
                            s.strip()
                            for s in bundle_str.split(",")
                            if s.strip()
                        )
                        if bundle_items:
                            bidder.add_bid(bundle_items, val)

            if st.button("Set auction", use_container_width=True):
                st.session_state["auction"] = auction
                st.session_state["results"] = None

        # ── solve button ─────────────────────────────────────────────────
        st.divider()
        if st.button("Solve Auction", type="primary", use_container_width=True):
            if "auction" in st.session_state:
                auc = st.session_state["auction"]
                vcg_result = compute_vcg_payments(auc)
                core_check = is_in_core(
                    auc,
                    vcg_result.allocation,
                    vcg_result.payments,
                    max_coalition_size=min(len(auc.bidders), 6),
                )
                st.session_state["results"] = {
                    "vcg": vcg_result,
                    "core": core_check,
                }
            else:
                st.warning("Please set up an auction first.")

    # ── main area ────────────────────────────────────────────────────────
    if "auction" not in st.session_state:
        st.info(
            "Configure an auction in the sidebar and click "
            "**Set auction** or **Generate auction**."
        )
        return

    auction = st.session_state["auction"]

    # Show current auction
    st.subheader("Current Auction")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Items", len(auction.items))
    with col2:
        st.metric("Bidders", len(auction.bidders))

    # Show bids table
    bids_data = []
    for bid in auction.all_bids():
        bids_data.append({
            "Bidder": bid.bidder_id,
            "Bundle": ", ".join(sorted(bid.bundle)),
            "Value": f"{bid.value:.2f}",
        })
    if bids_data:
        st.dataframe(pd.DataFrame(bids_data), use_container_width=True)

    # ── results ──────────────────────────────────────────────────────────
    if "results" not in st.session_state or st.session_state["results"] is None:
        st.info("Click **Solve Auction** to run the WDP and VCG mechanism.")
        return

    results = st.session_state["results"]
    vcg = results["vcg"]
    core = results["core"]
    alloc = vcg.allocation

    st.divider()
    st.subheader("Allocation Result")

    # ── item cards coloured by winner ────────────────────────────────────
    winner_list = sorted(alloc.winner_ids)
    winner_colour = {w: _colour(i) for i, w in enumerate(winner_list)}

    item_cols = st.columns(min(len(auction.items), 8))
    for idx, item in enumerate(sorted(auction.items)):
        with item_cols[idx % len(item_cols)]:
            owner = alloc.item_assignment.get(item, "unallocated")
            bg = winner_colour.get(owner, "#757575")
            st.markdown(
                f'<div style="background:{bg};color:white;padding:12px;'
                f'border-radius:8px;text-align:center;margin:4px 0;">'
                f'<b>{item}</b><br><small>{owner}</small></div>',
                unsafe_allow_html=True,
            )

    # ── metrics row ──────────────────────────────────────────────────────
    st.subheader("Metrics")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Social Welfare", f"{vcg.total_welfare:.2f}")
    with m2:
        st.metric("VCG Revenue", f"{vcg.revenue:.2f}")
    with m3:
        st.metric("First-Price Revenue", f"{vcg.first_price_revenue():.2f}")
    with m4:
        st.metric("In Core?", "Yes" if core.is_core else "No")

    # ── payment comparison ───────────────────────────────────────────────
    st.subheader("Payment Comparison: VCG vs First-Price")
    fp = vcg.first_price_payments()
    pay_data = []
    for bidder_id in sorted(alloc.winner_ids):
        pay_data.append({
            "Bidder": bidder_id,
            "Won Bundle": ", ".join(sorted(alloc.bidder_bundle(bidder_id))),
            "Value": f"{alloc.bidder_value(bidder_id):.2f}",
            "VCG Payment": f"{vcg.payments.get(bidder_id, 0):.2f}",
            "First-Price Payment": f"{fp.get(bidder_id, 0):.2f}",
            "VCG Surplus": f"{vcg.bidder_surplus().get(bidder_id, 0):.2f}",
        })

    if pay_data:
        st.dataframe(pd.DataFrame(pay_data), use_container_width=True)

    # ── bar chart ────────────────────────────────────────────────────────
    chart_data = pd.DataFrame({
        "Bidder": sorted(alloc.winner_ids),
        "VCG": [vcg.payments.get(b, 0) for b in sorted(alloc.winner_ids)],
        "First-Price": [fp.get(b, 0) for b in sorted(alloc.winner_ids)],
    }).set_index("Bidder")
    st.bar_chart(chart_data)

    # ── core pricing details ─────────────────────────────────────────────
    st.subheader("Core Pricing Analysis")
    if core.is_core:
        st.success("VCG payments are in the core. No coalition can profitably block.")
    else:
        st.warning(
            f"VCG payments are NOT in the core. "
            f"{len(core.violated_coalitions)} coalition(s) can block."
        )
        for coalition, deficit in core.violated_coalitions[:5]:
            st.write(
                f"  Coalition {sorted(coalition)}: deficit = {deficit:.2f}"
            )

    # Show core bounds
    bounds_data = []
    for bidder_id, (lo, hi) in sorted(core.payment_bounds.items()):
        bounds_data.append({
            "Bidder": bidder_id,
            "Min Core Payment": f"{lo:.2f}",
            "Max Core Payment (IR)": f"{hi:.2f}",
            "VCG Payment": f"{vcg.payments.get(bidder_id, 0):.2f}",
        })
    if bounds_data:
        st.dataframe(pd.DataFrame(bounds_data), use_container_width=True)


if __name__ == "__main__":
    main()
