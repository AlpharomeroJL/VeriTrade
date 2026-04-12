/** Single place for operator-visible timestamps (local vs UTC). */

export type TimeDisplayMode = "local" | "utc";

const TZ: Record<TimeDisplayMode, string | undefined> = {
  local: undefined,
  utc: "UTC",
};

/** Proof trail, activity, API ISO strings — always 24h, consistent month/day order. */
export function formatOperatorTimestamp(iso: string, mode: TimeDisplayMode): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const opts: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: TZ[mode],
  };
  const formatted = d.toLocaleString("en-GB", opts);
  return mode === "utc" ? `${formatted} UTC` : formatted;
}

/** Chart time axis (unix seconds from Lightweight Charts). */
export function formatChartAxisTime(unixSec: number, mode: TimeDisplayMode, hourlyLayout: boolean): string {
  const d = new Date(unixSec * 1000);
  if (Number.isNaN(d.getTime())) return "";
  if (hourlyLayout) {
    const opts: Intl.DateTimeFormatOptions = {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: TZ[mode],
    };
    const formatted = d.toLocaleString("en-GB", opts);
    return mode === "utc" ? `${formatted} UTC` : formatted;
  }
  const opts: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: TZ[mode],
  };
  const formatted = d.toLocaleString("en-GB", opts);
  return mode === "utc" ? `${formatted} UTC` : formatted;
}

export const TIME_DISPLAY_STORAGE_KEY = "vt_time_display";
