/** Shared UI bits for dashboard / shell (keeps App.tsx smaller). */

export function surfaceClass(extra = ""): string {
  return `vt-surface backdrop-blur-md ${extra}`;
}

export function Tip({ text }: { text: string }) {
  return (
    <span
      className="ml-1 inline-flex h-4 w-4 cursor-help select-none items-center justify-center rounded-full bg-white/[0.06] align-middle text-[9px] font-bold text-slate-500 hover:bg-white/[0.1] hover:text-slate-400"
      title={text}
      role="img"
      aria-label={text}
    >
      ?
    </span>
  );
}

export function Badge({
  label,
  tone,
  "data-testid": dataTestId,
}: {
  label: string;
  tone: "slate" | "emerald" | "amber" | "rose" | "sky" | "violet" | "indigo" | "gold";
  "data-testid"?: string;
}) {
  const tones: Record<string, string> = {
    slate: "bg-slate-800/90 text-slate-200 ring-white/10",
    emerald: "bg-emerald-500/10 text-emerald-200 ring-emerald-500/25",
    amber: "bg-amber-500/10 text-amber-200 ring-amber-500/25",
    rose: "bg-rose-500/10 text-rose-200 ring-rose-500/25",
    sky: "bg-sky-500/10 text-sky-200 ring-sky-500/25",
    violet: "bg-violet-500/10 text-violet-200 ring-violet-500/25",
    indigo: "bg-indigo-500/10 text-indigo-200 ring-indigo-500/25",
    gold: "bg-amber-400/10 text-amber-100 ring-amber-400/30",
  };
  return (
    <span
      data-testid={dataTestId}
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ring-1 ${tones[tone]}`}
    >
      {label}
    </span>
  );
}
