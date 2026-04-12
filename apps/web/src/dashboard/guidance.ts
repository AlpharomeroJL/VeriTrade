/** State-based “what next?” copy — no React. */

export type OverviewForGuidance = {
  latest_signal: unknown | null;
  latest_risk: unknown | null;
  latest_execution: unknown | null;
  control: { manual_pause: boolean };
} | null;

export type GuidanceAction =
  | { type: "post"; label: string; path: string }
  | { type: "scroll"; label: string; targetId: string };

export type Guidance = {
  headline: string;
  body: string;
  primary?: GuidanceAction;
  secondary?: GuidanceAction;
};

export function getGuidance(o: OverviewForGuidance, traceLen: number): Guidance {
  if (!o) {
    return {
      headline: "Loading your workspace",
      body: "Hang on—we’re fetching the latest state from the demo API.",
    };
  }

  const hasSignal = o.latest_signal != null;
  const hasExec = o.latest_execution != null;
  const manual = o.control.manual_pause;
  const riskVerdict =
    o.latest_risk && typeof o.latest_risk === "object" && o.latest_risk !== null && "verdict" in o.latest_risk
      ? String((o.latest_risk as { verdict?: string }).verdict)
      : "";

  if (!hasSignal) {
    return {
      headline: "Step 1 — Load sample data",
      body: "Nothing is on screen yet. One click seeds a safe demo portfolio and tape so the rest of the console lights up.",
      primary: { type: "post", label: "Seed demo data", path: "/demo/seed" },
    };
  }

  if (!hasExec) {
    if (riskVerdict === "block") {
      return {
        headline: "Risk blocked this cycle — valid outcome",
        body: "Use a different preset (safe market or oversized trim) to walk allow vs reduced approval. The proof trail still captured signal and risk artifacts.",
        primary: { type: "scroll", label: "Open proof trail", targetId: "proof-trail" },
        secondary: { type: "scroll", label: "Demo scenario presets", targetId: "scenario-presets" },
      };
    }
    if (riskVerdict === "escalate_for_review") {
      return {
        headline: "Escalated for review — no automatic fill",
        body: "Confidence dipped below policy threshold. Try a demo preset for a predictable allow/trim path, or adjust policy in the backend for this session.",
        primary: { type: "scroll", label: "Demo scenario presets", targetId: "scenario-presets" },
        secondary: { type: "scroll", label: "Open proof trail", targetId: "proof-trail" },
      };
    }
    return {
      headline: "Step 2 — Run the full loop once",
      body: "You’ve got sample data. Run a single cycle to watch the idea become a checked plan and a simulated execution result.",
      primary: { type: "post", label: "Run one cycle", path: "/demo/run-once" },
      secondary:
        traceLen > 0
          ? { type: "scroll", label: "Peek at proof trail", targetId: "proof-trail" }
          : undefined,
    };
  }

  if (manual) {
    return {
      headline: "Risk pause is on",
      body: "An operator flipped the manual risk pause. Clear it when you want autonomous runs to continue.",
      primary: { type: "post", label: "Clear risk pause", path: "/control/manual-pause?enabled=false" },
      secondary: { type: "scroll", label: "See proof trail", targetId: "proof-trail" },
    };
  }

  return {
    headline: "You’re caught up — explore the proof",
    body: "Scroll the Proof trail to see each step left a durable record. Optional: try Risk pause to see the safety switch.",
    primary: { type: "scroll", label: "Open proof trail", targetId: "proof-trail" },
    secondary: { type: "post", label: "Try risk pause", path: "/control/manual-pause?enabled=true" },
  };
}

/** Which quick-start step (0–3) should appear “active”. */
export function quickStartActiveStep(o: OverviewForGuidance): number {
  if (!o || !o.latest_signal) return 0;
  if (!o.latest_execution) return 1;
  return 2;
}
