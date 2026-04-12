# VeriTrade — Demo script (under 3 minutes)

**Finalist path:** Use **[submission/demo-flow-finalist.md](submission/demo-flow-finalist.md)** for the exact 2–3 minute flow aligned with the premium UI. This file stays as extended backup detail.

**Goal:** Show **combined submission** value: **Kraken-ready surface** + **trustless-agent-style** identity, **binding intents**, **validation artifacts** — not alpha.  
**Prereqs:** [README.md](../README.md) quick start; API + web running; browser zoom ~100% for screenshots.  
**Rubric map:** [challenge-alignment.md](challenge-alignment.md) · **Screenshots:** [submission/finalist-screenshots.md](submission/finalist-screenshots.md)

---

## 0:00–0:20 — Hook + safety

1. Full-screen the **dashboard**. Point to the top badges: **Paper only**, **Mode**, **Risk** verdict, **Exec** status.
2. One line: *“Every action is policy-checked, intent-recorded, and artifact-logged before a simulated fill.”*
3. Expand **Why this is trustworthy** (optional if time tight — badges already tell the story).

## 0:20–0:45 — Reset to a clean story

4. Click **1 · Seed demo** — narrate: clean tables, **running** mode, mock market + starting equity.
5. Confirm **Performance** shows equity; **pipeline** steps are empty or partial until the first run.

## 0:45–1:45 — One full governed cycle

6. Click **2 · Run cycle**. Walk the **decision pipeline** strip: **signal → risk → intent → execution** lights up.
7. **Signal** card: type, confidence, rationale (strategy is illustrative).
8. **Risk** card: verdict; if **allow_with_reduction**, call out requested vs approved on **Intent**.
9. **Execution** card: `paper`, `filled` or `rejected`.
10. **Artifact trace** (scroll): chronological proof — same stages as the pipeline, persisted.

## 1:45–2:30 — Trust + risk story

11. **Performance**: equity, P&amp;L, **drawdown** bar (exposure to peak-hint, not a fund audit).
12. **Risk pause**: click **Risk pause**, then **2 · Run cycle** — narrate that autonomous runs stop; operator must use **Step** or clear pause.
13. **Pause** mode: **Run cycle** no-ops when paused; **Step (paused)** runs **one** inspected cycle — *“bounded autonomy.”*

## 2:30–3:00 — Close strong

14. **Stop** — system halted; **Start** to recover.
15. Closing line: *“VeriTrade optimizes for **credible controls and auditability** — the right slice for agentic trading in real institutions.”*

---

## Backup lines (if blocked or escalated)

- **Blocked:** “Risk refused the trade — see artifact **risk** reasons; no intent execution.”
- **Escalated:** “Below-confidence signal escalates — intent exists for review, no fill.”

## Screenshot checklist

Use the full list: [submission/screenshot-checklist.md](submission/screenshot-checklist.md) (agent panel, intent hash, trace, etc.).

## API-only (rehearsal)

```http
POST /demo/seed
POST /demo/run-once
GET /overview
GET /activity
```

Trust narrative: [trust-and-risk.md](trust-and-risk.md).
