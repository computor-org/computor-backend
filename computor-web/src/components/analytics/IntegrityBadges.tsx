import { FLAG_LABEL, FLAG_TITLE, type IntegrityFlagCounts, type IntegrityFlagKind } from './integrity';

const KINDS: IntegrityFlagKind[] = ['velocity', 'low_iteration', 'tutor_concern'];

const TONE: Record<IntegrityFlagKind, string> = {
  velocity: 'bg-orange-50 text-orange-700 ring-orange-200',
  low_iteration: 'bg-amber-50 text-amber-700 ring-amber-200',
  tutor_concern: 'bg-rose-50 text-rose-700 ring-rose-200',
};

/** Compact flag counts. Numbers show for every student; `worstBand` only adds a
 * dot so the lecturer can triage the worst cases first. The flags are review
 * cues, never verdicts. */
export default function IntegrityBadges({
  flags,
  worstBand = false,
  size = 'sm',
}: {
  flags: IntegrityFlagCounts | undefined;
  worstBand?: boolean;
  size?: 'sm' | 'md';
}) {
  if (!flags || flags.total === 0) {
    return <span className="text-xs text-gray-300">—</span>;
  }
  const pad = size === 'md' ? 'px-2 py-0.5 text-xs' : 'px-1.5 py-0.5 text-[10px]';
  return (
    <span className="inline-flex items-center gap-1">
      {worstBand && (
        <span
          className="h-1.5 w-1.5 rounded-full bg-rose-500"
          title="Among the most-flagged students"
          aria-label="most flagged"
        />
      )}
      {KINDS.filter((k) => flags[k] > 0).map((k) => (
        <span
          key={k}
          title={`${FLAG_TITLE[k]} (${flags[k]})`}
          className={`inline-flex items-center gap-0.5 rounded ring-1 ring-inset font-medium ${pad} ${TONE[k]}`}
        >
          {FLAG_LABEL[k]} {flags[k]}
        </span>
      ))}
    </span>
  );
}
