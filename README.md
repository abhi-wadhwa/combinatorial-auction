# combinatorial-auction

combinatorial auctions — when bidders care about bundles, not individual items. computationally hard, economically important.

## what this is

- **winner determination** — the NP-hard core: which bids to accept? solved via ILP
- **VCG payments** — truthful payments. requires solving the WDP n+1 times
- **core pricing** — VCG can be too low. core constraints ensure no coalition wants to deviate
- **ascending auction (CCA)** — the iterative format used for spectrum auctions worldwide

## running it

```bash
pip install -r requirements.txt
python main.py
```

## why it matters

with n items there are 2^n possible bundles, so even representing preferences is exponential. the winner determination problem is NP-hard (weighted set packing). but modern ILP solvers handle realistic instances because the constraint matrices have nice structure. this is what governments use to sell wireless spectrum.
