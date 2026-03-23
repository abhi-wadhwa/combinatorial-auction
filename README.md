# Combinatorial Auction Simulator

A complete combinatorial auction engine featuring Winner Determination via Integer Linear Programming, Vickrey-Clarke-Groves (VCG) payment computation, core pricing verification, multiple bidding languages, and an interactive Streamlit dashboard.

## Background

### Combinatorial Auctions

In a **combinatorial auction**, multiple indivisible items are sold simultaneously and bidders can place bids on *bundles* (subsets) of items. This is critical when items exhibit **complementarities** (a bundle is worth more than the sum of its parts) or **substitutabilities** (items are interchangeable).

Real-world applications include spectrum licence auctions (FCC), airport landing slots, and procurement auctions.

### Winner Determination Problem (WDP)

The WDP is a **weighted set-packing** problem. Given a set of items $M = \{1, \dots, m\}$ and a set of bids $B = \{(S_j, v_j)\}_{j=1}^{n}$ where $S_j \subseteq M$ is the bundle and $v_j \geq 0$ is the bid value, the WDP selects winning bids to maximise social welfare:

$$\max \sum_{j=1}^{n} v_j \cdot x_j$$

subject to:

$$\sum_{j : i \in S_j} x_j \leq 1 \quad \forall \, i \in M$$

$$x_j \in \{0, 1\} \quad \forall \, j$$

The first constraint ensures each item is allocated at most once. The WDP is NP-hard in general, but practical instances are solved efficiently with modern ILP solvers. This project uses **PuLP** with the **CBC** solver.

### VCG Mechanism

The **Vickrey-Clarke-Groves** mechanism is the unique efficient, strategyproof, and individually rational mechanism (up to additions of bidder-independent terms). Each winning bidder $i$ pays the **externality** they impose on other participants:

$$p_i = V^*(N \setminus \{i\}) - \left[ V^*(N) - v_i(S_i^*) \right]$$

where:
- $V^*(N)$ is the optimal social welfare with all bidders.
- $V^*(N \setminus \{i\})$ is the optimal welfare when bidder $i$ is excluded.
- $v_i(S_i^*)$ is bidder $i$'s value for their allocated bundle $S_i^*$.

**Key properties:**
- **Truthfulness**: reporting true valuations is a dominant strategy.
- **Individual rationality**: $p_i \leq v_i(S_i^*)$ for every winner.
- **Efficiency**: the allocation maximises total value.

Computing VCG payments requires solving $n+1$ ILPs: one with all bidders and one per winner with that winner excluded.

### Core Pricing

The **core** of the auction is the set of payment vectors $(p_1, \dots, p_n)$ such that no coalition of bidders and the auctioneer can profitably deviate. A payment vector is in the core if:

$$\sum_{i \in C} p_i \geq V^*(C) - \left[ V^*(N) - \sum_{i \in C} v_i(S_i^*) \right] \quad \forall \, C \subseteq N$$

VCG payments are **not always in the core**, particularly when items are complements (the "threshold problem"). When VCG payments lie outside the core, the auctioneer has an incentive to deviate. Core-selecting auctions (e.g., the pay-as-bid combinatorial clock auction used by the FCC) address this by finding minimum-revenue core points.

## Features

- **WDP solver** -- weighted set-packing ILP via PuLP + CBC
- **VCG payments** -- externality-based truthful payments ($n+1$ ILPs)
- **Core pricing check** -- verify whether VCG payments are in the core; detect blocking coalitions
- **Bidding languages** -- XOR bids, OR bids, additive-OR bids, bundle bids
- **Demand generators** -- synthetic bidders with additive, substitutes, complements, or single-minded valuations
- **Streamlit dashboard** -- interactive auction setup, allocation visualisation, payment comparison
- **CLI** -- quick demos and random auction generation from the terminal

## Project Structure

```
combinatorial-auction/
├── src/
│   ├── core/
│   │   ├── auction.py          # Auction data structures
│   │   ├── wdp.py              # Winner determination ILP
│   │   ├── vcg.py              # VCG payments
│   │   ├── core_pricing.py     # Core check
│   │   ├── bidding.py          # Bidding languages
│   │   └── generators.py       # Synthetic demand
│   ├── viz/
│   │   └── app.py              # Streamlit UI
│   └── cli.py                  # Command-line interface
├── tests/
│   ├── test_wdp.py
│   ├── test_vcg.py
│   ├── test_core.py
│   └── test_bidding.py
├── examples/
│   └── demo.py
├── pyproject.toml
├── Makefile
├── Dockerfile
└── .github/workflows/ci.yml
```

## Quick Start

### Install

```bash
# Clone
git clone https://github.com/abhi-wadhwa/combinatorial-auction.git
cd combinatorial-auction

# Install (editable)
pip install -e ".[dev]"
```

### Run the demo

```bash
python -m src.cli demo
```

### Launch Streamlit dashboard

```bash
streamlit run src/viz/app.py
```

### Run tests

```bash
pytest tests/ -v
```

### Docker

```bash
docker build -t combinatorial-auction .
docker run -p 8501:8501 combinatorial-auction
# Open http://localhost:8501
```

## Usage Example

```python
from src.core.auction import Auction
from src.core.vcg import compute_vcg_payments
from src.core.core_pricing import is_in_core

# Create auction
auction = Auction(items={"A", "B", "C"})

alice = auction.add_bidder("Alice")
alice.add_bid(frozenset(["A", "B"]), 10.0)
alice.add_bid(frozenset(["A"]), 5.0)

bob = auction.add_bidder("Bob")
bob.add_bid(frozenset(["B", "C"]), 12.0)

# Solve VCG
vcg = compute_vcg_payments(auction)
print(f"Social welfare: {vcg.total_welfare}")
print(f"VCG payments: {vcg.payments}")
print(f"VCG revenue: {vcg.revenue}")

# Check core
core = is_in_core(auction, vcg.allocation, vcg.payments)
print(f"In core: {core.is_core}")
```

## References

- Cramton, P., Shoham, Y., & Steinberg, R. (2006). *Combinatorial Auctions*. MIT Press.
- Vickrey, W. (1961). Counterspeculation, auctions, and competitive sealed tenders. *Journal of Finance*.
- Clarke, E. H. (1971). Multipart pricing of public goods. *Public Choice*.
- Groves, T. (1973). Incentives in teams. *Econometrica*.
- de Vries, S., & Vohra, R. V. (2003). Combinatorial auctions: A survey. *INFORMS Journal on Computing*.
- Day, R., & Milgrom, P. (2008). Core-selecting package auctions. *International Journal of Game Theory*.

## License

MIT
