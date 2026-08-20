'use client';

/**
 * Shared progress bar for staged, long-running work (workspace startup, image
 * builds, template pushes).
 *
 * Deliberately separate from `components/progress/ProgressBar`, which reports a
 * *measured* quantity — points earned, submissions passed — and is styled by an
 * inline hex colour chosen by its chart callers. This one reports *how far
 * along a process is*, so it speaks in semantic tones that match the Badge
 * palette and supports the state that matters here and never occurs there: a
 * stage whose completion is unknown, drawn as a sweep rather than a fill.
 */

export type ProgressTone = 'blue' | 'green' | 'red' | 'amber' | 'gray';

const FILL_CLS: Record<ProgressTone, string> = {
  blue: 'bg-blue-500',
  green: 'bg-green-500',
  red: 'bg-red-500',
  amber: 'bg-amber-500',
  gray: 'bg-gray-400',
};

const SIZE_CLS = {
  xs: 'h-1',
  sm: 'h-1.5',
  md: 'h-2',
} as const;

export default function ProgressTrack({
  value,
  tone = 'blue',
  size = 'sm',
  active = false,
  label,
  className = '',
}: {
  /** 0–100. Clamped. */
  value: number;
  tone?: ProgressTone;
  size?: keyof typeof SIZE_CLS;
  /**
   * The work is still moving: the filled part gets a sweeping highlight so a
   * stage that sits at one width for a minute does not read as stalled.
   */
  active?: boolean;
  /**
   * What the bar is measuring, for screen readers — e.g. "Starting python-dev".
   * The visible stage text lives next to the bar, not inside it.
   */
  label: string;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));

  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      aria-label={label}
      className={`${SIZE_CLS[size]} w-full overflow-hidden rounded-full bg-sunken ${className}`}
    >
      <div
        className={`${SIZE_CLS[size]} overflow-hidden rounded-full transition-[width] duration-500 ease-out ${FILL_CLS[tone]}`}
        style={{ width: `${pct}%` }}
      >
        {active && (
          // Sits inside the fill and is clipped by it, so the sweep travels the
          // filled portion only — the empty remainder stays honestly empty.
          <div className="h-full w-1/4 rounded-full bg-surface/40 progress-sweep" />
        )}
      </div>
    </div>
  );
}
