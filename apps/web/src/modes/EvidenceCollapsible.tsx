import type { ReactNode } from "react";
import { surfaceClass } from "../dashboard/uiPrimitives";

export function EvidenceCollapsible({
  eyebrow,
  title,
  subtitle,
  defaultOpen,
  children,
  /** Muted chrome so the hero (live story) stays visually primary */
  tone = "default",
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  defaultOpen: boolean;
  children: ReactNode;
  tone?: "default" | "secondary";
}) {
  const shell =
    tone === "secondary"
      ? "scroll-mt-24 overflow-hidden rounded-2xl border border-white/[0.04] bg-white/[0.015] ring-0 opacity-95"
      : surfaceClass("scroll-mt-24 overflow-hidden");
  const titleCls = tone === "secondary" ? "mt-2 text-base font-semibold text-slate-200" : "mt-2 text-lg font-semibold text-white";
  return (
    <details className={`group ${shell}`} {...({ defaultOpen } as Record<string, unknown>)}>
      <summary className="cursor-pointer list-none border-b border-white/[0.04] px-6 py-4 sm:px-8 [&::-webkit-details-marker]:hidden">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-600">{eyebrow}</p>
            <p className={titleCls}>{title}</p>
            {subtitle ? <p className="mt-1 max-w-2xl text-xs leading-relaxed text-slate-600">{subtitle}</p> : null}
          </div>
          <span className="text-[11px] font-medium text-slate-600 transition group-open:text-teal-400/80">Tap to expand</span>
        </div>
      </summary>
      <div className="space-y-12 px-0 pb-12 pt-8">{children}</div>
    </details>
  );
}
