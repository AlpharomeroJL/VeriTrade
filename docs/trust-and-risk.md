# Why VeriTrade Is Trustworthy (Judge Brief)

This page is the **submission narrative** for trust and risk discipline. Pair it with the live dashboard: **badges**, **validation artifact trace**, and **operator controls**.

**Hackathon rubric map:** [challenge-alignment.md](challenge-alignment.md) · **Kraken / ERC-8004 breakdown:** [map-kraken.md](map-kraken.md), [map-erc8004.md](map-erc8004.md), [erc8004-alignment.md](erc8004-alignment.md)

## One sentence

**VeriTrade proves every trading action** — signal → policy → canonical intent → execution — **before** capital moves, with a **persistent artifact trail** and **paper-only** default.

## What “trust” means here (not hype)

| Mechanism | What the judge sees |
|-----------|---------------------|
| **Governed pipeline** | No execution without a recorded **risk verdict** and **trade intent**. |
| **Explicit risk outcomes** | Verdicts: `allow`, `allow_with_reduction`, `block`, `escalate_for_review` with machine-readable reasons. |
| **Intent before execution** | Intent row exists **prior** to paper fill; sizes show requested vs approved when policy clamps exposure. |
| **Artifact trail** | Each stage writes a durable **artifact** (DB + JSON file) for audit and replay-style inspection. |
| **Operator control** | **Start / Pause / Stop** and **Step** when paused — autonomy is bounded by a human-in-the-loop console. |
| **Paper by default** | `TRADING_MODE=paper`, `ALLOW_REAL_ORDERS=false` — demo cannot accidentally place live orders without deliberate env changes. |

## What we are *not* claiming

- We are **not** claiming superior alpha or production-ready execution.
- We **are** claiming a **credible control architecture** suitable for regulated or institutional workflows **as a thin slice**.

## Demo alignment (under 3 minutes)

1. Point at **Paper** + **system mode** badges.  
2. **Seed** → **Run cycle** → trace **Signal → Risk → Intent → Execution** in the timeline.  
3. Zoom **performance** (equity, drawdown).  
4. **Pause** → show **Run** blocked → **Step** still advances one gated cycle.  

Full wording: [demo-script.md](demo-script.md).
