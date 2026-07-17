// Formatting + safe-read helpers shared across views.

export function formatWibDate(value: unknown): string {
  if (!value) return "-";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("id-ID", {
    timeZone: "Asia/Jakarta",
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(date);
}

export function formatMs(value: unknown): string {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number)) return "0 ms";
  return `${number >= 100 ? number.toFixed(0) : number.toFixed(1)} ms`;
}

export function readNestedString(source: unknown, path: string[]): string {
  let current: unknown = source;
  for (const key of path) {
    if (!current || typeof current !== "object" || !(key in current)) return "";
    current = (current as Record<string, unknown>)[key];
  }
  return typeof current === "string" ? current : "";
}
