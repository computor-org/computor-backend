'use client';

import Badge from '@/src/components/Badge';
import { flagTone, sortFlags } from '@/src/utils/courseAnalytics';
import type { FlagReason, FlagRule } from 'types/generated';

/**
 * Rule-based flags ("Auffälligkeiten") with the reason each one fired.
 *
 * A flag is a prompt to look, not a verdict: every entry names the rule and
 * the numbers behind it, and `FlagRules` lists all rules with their
 * thresholds so nothing is a black box.
 */
export function FlagChips({ flags }: { flags: FlagReason[] }) {
  if (flags.length === 0) return <span className="text-xs text-subtle">—</span>;
  const titles = new Map<string, FlagReason>();
  for (const f of sortFlags(flags)) if (!titles.has(f.code)) titles.set(f.code, f);
  return (
    <div className="flex flex-wrap gap-1">
      {[...titles.values()].map((f) => (
        <span key={f.code} title={flags.filter((x) => x.code === f.code).map((x) => x.reason).join('\n')}>
          <Badge tone={flagTone(f.severity)}>{f.title}</Badge>
        </span>
      ))}
    </div>
  );
}

export default function FlagList({ flags }: { flags: FlagReason[] }) {
  if (flags.length === 0) {
    return <p className="text-sm text-muted">No flags. None of the rules below applies.</p>;
  }
  return (
    <ul className="space-y-2">
      {sortFlags(flags).map((f, i) => (
        <li key={`${f.code}-${f.course_content_id ?? ''}-${i}`} className="flex flex-wrap items-baseline gap-2">
          <Badge tone={flagTone(f.severity)}>{f.title}</Badge>
          {f.course_content_title && (
            <span className="text-sm font-medium text-fg">{f.course_content_title}</span>
          )}
          <span className="text-sm text-body">{f.reason}</span>
        </li>
      ))}
    </ul>
  );
}

export function FlagRules({ rules }: { rules: FlagRule[] }) {
  if (rules.length === 0) return null;
  return (
    <details className="text-xs text-muted">
      <summary className="cursor-pointer select-none">How flags are computed</summary>
      <ul className="mt-2 space-y-1 list-disc pl-5">
        {rules.map((r) => (
          <li key={r.code}>
            <span className="font-medium text-body">{r.title}:</span> {r.description}
          </li>
        ))}
      </ul>
    </details>
  );
}
