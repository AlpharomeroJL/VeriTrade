export function SectionHead({ eyebrow, title, hint }: { eyebrow: string; title: string; hint?: string }) {
  return (
    <div className="border-b border-white/[0.04] px-8 py-6">
      <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">{eyebrow}</p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-xl font-semibold tracking-tight text-white">{title}</h2>
        {hint ? <p className="max-w-md text-sm leading-relaxed text-slate-500">{hint}</p> : null}
      </div>
    </div>
  );
}
