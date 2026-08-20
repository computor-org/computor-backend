'use client';

import { inputCls } from '@/src/components/ui/tokens';

/**
 * Tri-state student-visibility control (issue #338).
 *
 * `visible` is nullable on both Course and CourseContent, and the three states
 * are genuinely distinct, so this cannot be a checkbox:
 *
 *   null   inherit from the parent unit, and ultimately from the course
 *   true   explicitly visible
 *   false  hidden from students, along with everything beneath it
 *
 * `false` is a veto: a child set to `true` does NOT become visible again while
 * an ancestor hides it. That is why the "visible" option is worded as a local
 * statement rather than a promise -- the copy is doing real work here, because
 * the obvious reading of a checkbox would be wrong.
 */

export type VisibilityValue = boolean | null;

/** Parse the select's string value back to the tri-state it represents. */
export function parseVisibility(raw: string): VisibilityValue {
  if (raw === 'visible') return true;
  if (raw === 'hidden') return false;
  return null;
}

/** Render the tri-state as the select's string value. */
export function serializeVisibility(value: VisibilityValue): string {
  if (value === true) return 'visible';
  if (value === false) return 'hidden';
  return 'inherit';
}

interface VisibilitySelectProps {
  value: VisibilityValue;
  onChange: (value: VisibilityValue) => void;
  /** Course-level control has no parent to inherit from. */
  scope: 'course' | 'content';
  /**
   * Resolved visibility from the server. When this is false while `value` is
   * not false, something above is hiding this node and the local setting is
   * being overridden -- worth saying out loud.
   */
  effective?: boolean;
  disabled?: boolean;
}

export default function VisibilitySelect({
  value,
  onChange,
  scope,
  effective,
  disabled,
}: VisibilitySelectProps) {
  const overriddenFromAbove = effective === false && value !== false;

  return (
    <div className="space-y-1">
      <select
        value={serializeVisibility(value)}
        onChange={(e) => onChange(parseVisibility(e.target.value))}
        disabled={disabled}
        className={inputCls}
      >
        <option value="inherit">
          {scope === 'course'
            ? 'Visible (default)'
            : 'Inherit from the unit above'}
        </option>
        <option value="visible">Visible</option>
        <option value="hidden">
          {scope === 'course'
            ? 'Hidden — hides the whole course content tree'
            : 'Hidden — hides this and everything under it'}
        </option>
      </select>

      {overriddenFromAbove && (
        <p className="text-xs text-warn-text">
          Currently hidden anyway: a unit above this one, or the course itself,
          is hidden. Setting this to visible will not override that.
        </p>
      )}

      {value === false && (
        <p className="text-xs text-muted">
          Students will not see this in their assignment tree and cannot test or
          submit. Their files, existing tests and submissions are untouched and
          reappear when you make it visible again.
        </p>
      )}
    </div>
  );
}
