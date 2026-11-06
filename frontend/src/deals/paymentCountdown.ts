/**
 * Timestamp parsing and retry countdown calculation helpers.
 */

export function parseTimestamp(timestamp: string | null | undefined): number | null {
  if (!timestamp || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(timestamp)) return null;
  const targetMs = Date.parse(timestamp);
  return Number.isFinite(targetMs) ? targetMs : null;
}

export function formatCountdown(timestamp: string | null | undefined, nowMs: number): number | null {
  const targetMs = parseTimestamp(timestamp);
  return targetMs === null ? null : Math.max(0, Math.round((targetMs - nowMs) / 1000));
}
