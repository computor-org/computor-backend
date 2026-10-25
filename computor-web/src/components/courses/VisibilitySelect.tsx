'use client';

import { inputCls } from '@/src/components/ui/tokens';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const COPY = {
  de: {
    visibleDefault: 'Sichtbar (Standard)',
    inherit: 'Von der übergeordneten Einheit übernehmen',
    visible: 'Sichtbar',
    hiddenCourse: 'Verborgen: verbirgt den gesamten Inhaltsbaum des Kurses',
    hiddenContent: 'Verborgen: verbirgt diesen Inhalt und alles darunter',
    overridden: 'Derzeit trotzdem verborgen: Eine Einheit darüber oder der Kurs selbst ist verborgen. Wenn du diesen Inhalt auf sichtbar stellst, ändert das nichts daran.',
    hiddenNote: 'Studierende sehen das nicht in ihrem Aufgabenbaum und können nichts testen oder abgeben. Ihre Dateien, bisherigen Tests und Abgaben bleiben erhalten und erscheinen wieder, sobald du es sichtbar machst.',
  },
  en: {
    visibleDefault: 'Visible (default)',
    inherit: 'Inherit from the unit above',
    visible: 'Visible',
    hiddenCourse: 'Hidden — hides the whole course content tree',
    hiddenContent: 'Hidden — hides this and everything under it',
    overridden: 'Currently hidden anyway: a unit above this one, or the course itself, is hidden. Setting this to visible will not override that.',
    hiddenNote: 'Students will not see this in their assignment tree and cannot test or submit. Their files, existing tests and submissions are untouched and reappear when you make it visible again.',
  },
};

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
  const t = COPY[useUiLanguage()];
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
          {scope === 'course' ? t.visibleDefault : t.inherit}
        </option>
        <option value="visible">{t.visible}</option>
        <option value="hidden">
          {scope === 'course' ? t.hiddenCourse : t.hiddenContent}
        </option>
      </select>

      {overriddenFromAbove && (
        <p className="text-xs text-warn-text">
          {t.overridden}
        </p>
      )}

      {value === false && (
        <p className="text-xs text-muted">
          {t.hiddenNote}
        </p>
      )}
    </div>
  );
}
