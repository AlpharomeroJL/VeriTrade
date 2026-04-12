import { surfaceClass } from "../dashboard/uiPrimitives";

const STEPS: { n: number; title: string; body: string; lookFor: string; scrollId?: string; scrollLabel?: string }[] = [
  {
    n: 1,
    title: "Load demo data",
    body: "Seeds a safe portfolio and tape so every panel has something real to read.",
    lookFor: "Executive tiles and chart should wake up.",
    scrollId: "command-bar",
    scrollLabel: "Open command bar",
  },
  {
    n: 2,
    title: "Run one cycle",
    body: "Walks idea → safety → signed plan → simulated execution once.",
    lookFor: "Pipeline dots turn complete; proof trail gains rows.",
    scrollId: "command-bar",
    scrollLabel: "Open command bar",
  },
  {
    n: 3,
    title: "Read the safety decision",
    body: "See allow, trim, block, or review — same rules the autonomous loop uses.",
    lookFor: "Risk tile and pipeline risk stage update together.",
    scrollId: "scenario-presets",
    scrollLabel: "Try a preset",
  },
  {
    n: 4,
    title: "Inspect the proof trail",
    body: "Each row is a receipt written in order — human headline first.",
    lookFor: "Headlines match the pipeline order you just ran.",
    scrollId: "proof-trail",
    scrollLabel: "Jump to proof trail",
  },
  {
    n: 5,
    title: "Try blocked or reduced outcomes",
    body: "Presets force predictable endings so you trust the router.",
    lookFor: "Volatile preset stops before intent; oversized trims size.",
    scrollId: "scenario-presets",
    scrollLabel: "Open presets",
  },
];

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function GuidedDemoSteps() {
  return (
    <section className={`${surfaceClass("")} overflow-hidden`} aria-labelledby="guided-steps-heading">
      <div className="border-b border-white/[0.04] px-8 py-6">
        <p id="guided-steps-heading" className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">
          Guided path
        </p>
        <h2 className="mt-2 text-xl font-semibold text-white">Five steps to a full proof run</h2>
        <p className="mt-2 max-w-2xl text-xs leading-relaxed text-slate-600">
          One primary action per step. Complete them in order the first time; after that, use any mode freely.
        </p>
      </div>
      <ol className="list-none space-y-0 divide-y divide-white/[0.04]">
        {STEPS.map((s) => (
          <li key={s.n} className="px-8 py-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-mono text-[10px] font-semibold uppercase tracking-wider text-teal-500/90">Step {s.n}</p>
                <p className="mt-1 text-sm font-semibold text-white">{s.title}</p>
                <p className="mt-2 text-sm leading-relaxed text-slate-500">{s.body}</p>
                <p className="mt-2 text-xs text-slate-600">
                  <span className="font-medium text-slate-500">What to look for:</span> {s.lookFor}
                </p>
              </div>
              {s.scrollId ? (
                <button
                  type="button"
                  className="shrink-0 rounded-lg px-3 py-2 text-xs font-medium text-teal-200/90 ring-1 ring-teal-500/25 transition hover:bg-teal-500/10"
                  onClick={() => scrollToId(s.scrollId!)}
                >
                  {s.scrollLabel}
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
