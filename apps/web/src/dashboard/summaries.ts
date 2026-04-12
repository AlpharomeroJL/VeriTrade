/** Pure helpers for dashboard copy — no React. */

export type OverviewLike = {
  latest_signal: Record<string, unknown> | null;
  latest_risk: Record<string, unknown> | null;
  latest_intent: Record<string, unknown> | null;
  latest_execution: Record<string, unknown> | null;
};

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

function num(v: unknown): number | undefined {
  return typeof v === "number" && !Number.isNaN(v) ? v : undefined;
}

export type PipelineStageKind = "signal" | "risk" | "intent" | "execution";

export type PipelineVisualState = "waiting" | "complete" | "blocked" | "attention";

export function pipelineStageVisualState(kind: PipelineStageKind, o: OverviewLike | null): PipelineVisualState {
  if (!o) return "waiting";
  const sig = o.latest_signal;
  const risk = o.latest_risk;
  const intent = o.latest_intent;
  const ex = o.latest_execution;
  const verdict = str(risk?.verdict) ?? "";
  const exStatus = str(ex?.status) ?? "";

  switch (kind) {
    case "signal":
      return sig ? "complete" : "waiting";
    case "risk":
      if (!risk) return "waiting";
      if (verdict === "block") return "blocked";
      if (verdict === "escalate_for_review") return "attention";
      if (verdict === "skip") return "complete";
      return "complete";
    case "intent":
      if (verdict === "block") return "blocked";
      if (verdict === "skip") return "complete";
      if (!intent) return "waiting";
      return "complete";
    case "execution":
      if (verdict === "block") return "blocked";
      if (verdict === "skip") return "complete";
      if (!ex) return "waiting";
      if (exStatus === "rejected") return "blocked";
      return "complete";
    default:
      return "waiting";
  }
}

function trunc(s: string, max: number): string {
  const t = s.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

function reasonsMentionDuplicateAction(reasons: string | undefined): boolean {
  return (reasons ?? "").toLowerCase().includes("duplicate_action");
}

export function pipelineStageSummary(kind: PipelineStageKind, o: OverviewLike | null): string {
  if (!o) return "Seed the demo to populate this stage.";
  const sig = o.latest_signal;
  const risk = o.latest_risk;
  const intent = o.latest_intent;
  const ex = o.latest_execution;
  const verdict = str(risk?.verdict);
  const reasons = str(risk?.reasons);

  switch (kind) {
    case "signal": {
      if (!sig) return "Waiting for strategy signal.";
      const st = str(sig.signal_type) ?? "—";
      const asset = str(sig.asset) ?? "—";
      const conf = num(sig.confidence);
      const confStr = conf != null ? `${Math.round(conf * 100)}% confidence` : "—";
      return `${st} · ${asset} · ${confStr}`;
    }
    case "risk": {
      if (!sig) return "No signal yet — pipeline idle.";
      if (!risk) return "Signal received — awaiting router verdict.";
      const v = verdict ?? "—";
      const r = reasons ? trunc(reasons, 72) : "No reason text.";
      if (v === "skip") return `${v} — stood aside (${r})`;
      if (v === "block" && reasonsMentionDuplicateAction(reasons)) {
        return "block — duplicate guard: a very similar idea was handled recently, so the desk stood down instead of repeating the same action (technical reasons unchanged).";
      }
      return `${v} — ${r}`;
    }
    case "intent": {
      if (verdict === "block") return "No intent — risk router blocked the signal.";
      if (verdict === "skip") return "No intent — desk stood aside (no trade this cycle).";
      if (!risk) return "Awaiting risk decision before commitment.";
      if (!intent) return "Approved path — binding intent not yet materialized.";
      const action = str(intent.action) ?? "—";
      const asset = str(intent.asset) ?? "—";
      const approved = num(intent.approved_size);
      const status = str(intent.status) ?? "—";
      const sz = approved != null ? approved.toFixed(4) : "—";
      return `${action} ${asset} · size ${sz} · ${status}`;
    }
    case "execution": {
      if (verdict === "skip") return "No fill — stood aside before a committed plan.";
      if (!intent) return "No intent — venue path idle.";
      if (!ex) return "Intent signed — execution record pending.";
      const venue = str(ex.venue) ?? "—";
      const ot = str(ex.order_type) ?? "—";
      const status = str(ex.status) ?? "—";
      const fill = num(ex.fill_size);
      const fillHint = fill != null && fill > 0 ? ` · fill ${fill}` : "";
      return `${venue} · ${ot} · ${status}${fillHint}`;
    }
    default:
      return "—";
  }
}

/** Plain-English title shown first (technical subtitle below). */
export function stagePublicTitle(kind: PipelineStageKind): string {
  const m: Record<PipelineStageKind, string> = {
    signal: "Trading idea",
    risk: "Safety check",
    intent: "Committed trade plan",
    execution: "Execution result",
  };
  return m[kind];
}

/** Technical stage subtitle (small type in pipeline). */
export function stageChallengeSubtitle(kind: PipelineStageKind): string {
  const m: Record<PipelineStageKind, string> = {
    signal: "Strategy signal",
    risk: "Risk router",
    intent: "Signed intent",
    execution: "Venue path",
  };
  return m[kind];
}

/** @deprecated use stagePublicTitle — kept for imports that expect technical label */
export function pipelineStageLabel(kind: PipelineStageKind): string {
  return stagePublicTitle(kind);
}

export function pipelineStageRole(kind: PipelineStageKind): string {
  const m: Record<PipelineStageKind, string> = {
    signal: "Proposal",
    risk: "Policy gate",
    intent: "Binding commitment",
    execution: "Paper + Kraken draft",
  };
  return m[kind];
}

/** One-line “what is this step?” for beginners. */
export function pipelineStagePlainExplain(kind: PipelineStageKind): string {
  const m: Record<PipelineStageKind, string> = {
    signal: "The strategy proposes what it would like to do (buy/sell/hold) and how sure it is.",
    risk: "Automated rules decide if that idea is safe right now—approve, trim size, block, or escalate.",
    intent: "If allowed, we lock in a tamper-evident plan (hash) so the execution step can’t silently change it.",
    execution: "Simulated fills stand in for a venue; Kraken-style routing stays visible in the UI but stays gated.",
  };
  return m[kind];
}

/** Plain-English “what happened” for this run (complements technical summary). */
export function pipelineWhatHappenedPlain(kind: PipelineStageKind, o: OverviewLike | null): string {
  if (!o) return "Run the demo to see this stage light up.";
  const sig = o.latest_signal;
  const risk = o.latest_risk;
  const intent = o.latest_intent;
  const ex = o.latest_execution;
  const verdict = str(risk?.verdict);

  switch (kind) {
    case "signal":
      if (!sig) return "Waiting—no trading idea has been produced yet.";
      return `The desk published an idea for ${str(sig.asset) ?? "the asset"} (${str(sig.signal_type) ?? "signal"}).`;
    case "risk": {
      if (!sig) return "Idle until there is a trading idea to review.";
      if (!risk) return "The idea is in—waiting for the safety check to finish.";
      if (verdict === "block") {
        const rs = str(risk?.reasons);
        if (reasonsMentionDuplicateAction(rs)) {
          return "Duplicate guard: the desk declined because a very similar idea was handled recently—intentional suppression, not confusion.";
        }
        return "The safety check said no—nothing moves forward until the idea changes or conditions improve.";
      }
      if (verdict === "escalate_for_review") return "The router wants a human in the loop before trading proceeds.";
      if (verdict === "skip") return "The desk stood aside—no trade this cycle (not a hard safety block).";
      if (verdict === "allow_with_reduction") return "Approved, but only at a smaller size than requested.";
      return "Approved—the plan may continue to a committed trade plan.";
    }
    case "intent": {
      if (verdict === "block") return "Skipped—upstream safety check blocked the idea.";
      if (verdict === "skip") return "No signed plan—router ended the cycle without a commitment.";
      if (!intent) return "Approved in principle—binding commitment not written yet.";
      return "A signed plan exists linking the idea, policy version, and sizes.";
    }
    case "execution": {
      if (verdict === "block") return "No fill—execution never starts when the idea is blocked.";
      if (verdict === "skip") return "No fill—stood aside before execution applies.";
      if (!ex) return "Waiting for a paper or venue result after the plan is committed.";
      const st = str(ex.status) ?? "recorded";
      return `Result: ${st}. This is the simulated outcome recorded on the ledger for this run.`;
    }
    default:
      return "";
  }
}

export type ArtifactKind = PipelineStageKind;

export function artifactNarrativeLines(kind: ArtifactKind, data: Record<string, unknown> | null | undefined): string[] {
  if (!data || Object.keys(data).length === 0) return ["No artifact for this stage yet."];

  switch (kind) {
    case "signal": {
      const lines: string[] = [];
      const st = str(data.signal_type);
      const asset = str(data.asset);
      if (st || asset) lines.push([st, asset].filter(Boolean).join(" · ") || "Signal");
      const conf = num(data.confidence);
      if (conf != null) lines.push(`Confidence ${Math.round(conf * 100)}%`);
      const rat = str(data.rationale);
      if (rat) lines.push(trunc(rat, 220));
      const sid = str(data.strategy_id);
      if (sid) lines.push(`Strategy ${sid}`);
      return lines.length ? lines : ["Signal recorded."];
    }
    case "risk": {
      const lines: string[] = [];
      const v = str(data.verdict);
      if (v) lines.push(`Verdict: ${v}`);
      const rs = str(data.reasons);
      if (rs) lines.push(trunc(rs, 280));
      const req = num(data.requested_size);
      const app = num(data.approved_size);
      if (req != null || app != null) lines.push(`Requested ${req ?? "—"} → approved ${app ?? "—"}`);
      const pv = str(data.policy_version);
      if (pv) lines.push(`Policy ${pv}`);
      return lines.length ? lines : ["Risk decision recorded."];
    }
    case "intent": {
      const lines: string[] = [];
      const action = str(data.action);
      const asset = str(data.asset);
      if (action || asset) lines.push(`${action ?? "—"} ${asset ?? ""}`.trim());
      const app = num(data.approved_size);
      if (app != null) lines.push(`Approved notional ${app}`);
      const status = str(data.status);
      if (status) lines.push(`Status ${status}`);
      const hash = str(data.intent_commitment_sha256);
      if (hash) lines.push(`Commitment ${hash.slice(0, 16)}…${hash.slice(-8)}`);
      const rat = str(data.rationale);
      if (rat) lines.push(trunc(rat, 200));
      return lines.length ? lines : ["Intent recorded."];
    }
    case "execution": {
      const lines: string[] = [];
      const venue = str(data.venue);
      const ot = str(data.order_type);
      if (venue || ot) lines.push([venue, ot].filter(Boolean).join(" · "));
      const status = str(data.status);
      if (status) lines.push(`Status ${status}`);
      const msg = str(data.message);
      if (msg) lines.push(trunc(msg, 200));
      const fp = num(data.fill_price);
      const fs = num(data.fill_size);
      if (fp != null || fs != null) lines.push(`Fill price ${fp ?? "—"} · size ${fs ?? "—"}`);
      return lines.length ? lines : ["Execution recorded."];
    }
    default:
      return ["—"];
  }
}

export function activityHeadline(kind: string, summary: string, verdictOrStatus: string | null): string {
  const trimmed = summary.trim();
  if (!trimmed) return verdictOrStatus || "Event recorded.";

  try {
    const j = JSON.parse(trimmed) as Record<string, unknown>;
    if (j && typeof j === "object") {
      if (kind === "signal") {
        const parts = [str(j.signal_type), str(j.asset), num(j.confidence) != null ? `${Math.round((num(j.confidence) as number) * 100)}%` : ""].filter(
          Boolean,
        );
        if (parts.length) return parts.join(" · ");
      }
      if (kind === "risk") {
        const v = str(j.verdict);
        const r = str(j.reasons);
        if (v && r) return `${v} — ${trunc(r, 100)}`;
        if (v) return v;
      }
      if (kind === "intent") {
        const a = str(j.action);
        const as = str(j.asset);
        const st = str(j.status);
        if (a || as) return [a, as, st].filter(Boolean).join(" · ");
      }
      if (kind === "execution") {
        const ven = str(j.venue);
        const st = str(j.status);
        if (ven || st) return [ven, st].filter(Boolean).join(" · ");
      }
      const firstKey = Object.keys(j)[0];
      if (firstKey && j[firstKey] != null) return `${firstKey}: ${String(j[firstKey]).slice(0, 120)}`;
    }
  } catch {
    /* not JSON */
  }

  return trunc(trimmed.replace(/\s+/g, " "), 140);
}

const PROOF_LABELS: Record<string, string> = {
  signal: "Trading idea",
  risk: "Safety check",
  intent: "Committed plan",
  execution: "Execution result",
};

/** Proof trail row — plain stage name. */
export function proofTrailStageLabel(kind: string): string {
  return PROOF_LABELS[kind] ?? kind;
}

/** Short educational line under the headline (trust surface). */
export function activityExplanation(kind: string): string {
  if (kind === "signal") return "The strategy’s first output—what it would like to do before any safety filter.";
  if (kind === "risk")
    return "Proof the automated rules ran — line this up with the Safety check stage in the pipeline.";
  if (kind === "intent")
    return "The tamper-evident trade plan (intent commitment)—execution must match this snapshot.";
  if (kind === "execution") return "Paper fill or rejection—same shape as a real venue without moving money.";
  return "Stored for audit and replay.";
}
