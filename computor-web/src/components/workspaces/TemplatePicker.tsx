'use client';

import { useRef, type KeyboardEvent, type ReactNode } from 'react';
import type { CoderTemplate } from '@/src/types/workspaces';
import TemplateIcon from '@/src/components/workspaces/TemplateIcon';

const PREVIOUS_KEYS = ['ArrowUp', 'ArrowLeft'];
const NEXT_KEYS = ['ArrowDown', 'ArrowRight'];

/**
 * Card-style radio group for choosing a workspace template — shows the real
 * display metadata (display_name / description) that the template push
 * PATCHes into Coder.
 *
 * Cards rather than a list here on purpose: this is a one-off choice between a
 * handful of unlike things, where the icon and the sentence of description are
 * what you are choosing between. (Lists win where the rows are the same kind of
 * thing and you are comparing a value across them — see the build progress.)
 */
export default function TemplatePicker({
  templates,
  value,
  onChange,
  /** Where to send a maintainer who finds the list empty. */
  emptyHint,
}: {
  templates: CoderTemplate[];
  /** Raw template name of the selected template. */
  value: string;
  onChange: (name: string) => void;
  emptyHint?: ReactNode;
}) {
  const groupRef = useRef<HTMLDivElement>(null);
  const selectedIndex = templates.findIndex((t) => t.name === value);

  if (templates.length === 0) {
    return (
      <div className="text-sm text-muted space-y-1">
        <p>No templates available — Coder may still be initializing.</p>
        {emptyHint}
      </div>
    );
  }

  /**
   * Arrow keys move between options, as a radio group is expected to. Without
   * this the group is a row of buttons that each need their own Tab stop and
   * none of which respond to the keys a screen-reader user will try, which is
   * what `role="radiogroup"` promises they do.
   */
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const back = PREVIOUS_KEYS.includes(event.key);
    const forward = NEXT_KEYS.includes(event.key);
    if (!back && !forward) return;
    event.preventDefault();

    const from = selectedIndex === -1 ? 0 : selectedIndex;
    const next = (from + (forward ? 1 : -1) + templates.length) % templates.length;
    onChange(templates[next].name);
    // Selection follows focus in a radio group, so move focus with it.
    groupRef.current?.querySelectorAll('button')[next]?.focus();
  };

  return (
    <div
      ref={groupRef}
      role="radiogroup"
      onKeyDown={handleKeyDown}
      className="grid grid-cols-1 sm:grid-cols-2 gap-3"
    >
      {templates.map((t, index) => {
        const selected = t.name === value;
        return (
          <button
            key={t.id}
            type="button"
            role="radio"
            aria-checked={selected}
            // Roving tabindex: one Tab stop for the whole group, arrows within.
            // With nothing selected yet the first card takes it, or the group
            // would be unreachable by keyboard entirely.
            tabIndex={selected || (selectedIndex === -1 && index === 0) ? 0 : -1}
            onClick={() => onChange(t.name)}
            className={`flex items-start gap-3 rounded-lg border p-4 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-line focus-visible:ring-offset-2 ${
              selected
                ? 'border-accent ring-1 ring-accent bg-accent-wash/50'
                : 'border-rule bg-surface hover:border-rule-strong'
            }`}
          >
            <TemplateIcon template={t} />
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-fg">
                {t.display_name || t.name}
              </span>
              {t.description && (
                <span className="mt-0.5 block text-xs text-muted">{t.description}</span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}
