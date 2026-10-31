export function videoOpacity(time: number, duration: number): number {
  if (!Number.isFinite(duration) || duration <= 0) return 0;
  return Math.max(0, Math.min(1, time / 0.5, (duration - time) / 0.5));
}
