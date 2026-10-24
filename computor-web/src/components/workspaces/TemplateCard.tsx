'use client';

import type { ReactNode } from 'react';
import ProgressTrack from '@/src/components/ui/ProgressTrack';
import TemplateIcon from './TemplateIcon';
import {
  availabilityLabel,
  isUsable,
  templateLabel,
  type TemplateOption,
  UNAVAILABLE_REASON_DE,
} from './templateOptions';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

/**
 * One workspace type, as something to click.
 *
 * Shared by the workspaces page and the course pages so a type that cannot be
 * used looks the same wherever a user meets it: dimmed, not clickable, and
 * saying what it is waiting for. The alternative — the behaviour this
 * replaces — was a button that looked entirely normal and answered a click
 * with "Template 'bash-workspace' is not yet available", which reads as a bug
 * in the click rather than a fact about the server.
 *
 * A type mid-deployment also gets the bar and stage words the administration
 * page uses ("Building image"), so waiting users and the operator they will
 * eventually ask are looking at the same run.
 */
export default function TemplateCard({
  option,
  onClick,
  /** Second line when the type IS usable — e.g. 'Running', 'Create workspace'. */
  actionLabel,
  busy = false,
  /** Rendered at the right edge, e.g. a workspace status badge. */
  trailing,
  className = '',
}: {
  option: TemplateOption;
  onClick?: () => void;
  actionLabel?: ReactNode;
  busy?: boolean;
  trailing?: ReactNode;
  className?: string;
}) {
  const language = useUiLanguage();
  const usable = isUsable(option);
  const label = templateLabel(option);
  const stage = option.stage;
  const reason = language === 'de' && option.availability === 'unavailable' ? UNAVAILABLE_REASON_DE : option.reason;

  return (
    <button
      type="button"
      disabled={!usable || busy}
      onClick={onClick}
      // The reason is the hover explanation on a disabled card; on a usable one
      // there is nothing to explain that the card does not already say.
      title={reason ?? undefined}
      aria-label={usable ? undefined : `${label} — ${availabilityLabel(option, language)}`}
      className={`flex w-full items-center gap-3 rounded-lg border p-3 pr-4 text-left transition-colors ${
        usable
          ? 'border-rule bg-surface hover:border-accent-line hover:bg-accent-wash focus-visible:ring-2 focus-visible:ring-accent-line'
          : 'cursor-not-allowed border-rule bg-canvas opacity-60'
      } ${busy ? 'animate-pulse' : ''} ${className}`}
    >
      <TemplateIcon template={{ icon: option.icon, name: option.name }} />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold text-fg">{label}</span>
        <span
          className={`block truncate text-xs ${
            stage?.tone === 'red' ? 'text-danger-text' : 'text-muted'
          }`}
        >
          {usable ? actionLabel : availabilityLabel(option, language)}
        </span>
        {/*
          Only while the deployment is still going: a settled stage is a full
          bar saying what its label says (see templateTaskStage.settled).
        */}
        {stage && !stage.settled && (
          <ProgressTrack
            value={stage.percent}
            tone={stage.tone}
            active={stage.active}
            size="xs"
            className="mt-1.5"
            label={`${label}: ${stage.label}`}
          />
        )}
        {usable && stage && (
          <span className="mt-1 block truncate text-xs text-subtle">
            {language === 'de' ? 'Wird aktualisiert' : 'Updating'} · {stage.label}
          </span>
        )}
      </span>
      {trailing}
    </button>
  );
}

/**
 * Compact variant for the course cards, where a row of types has to fit under
 * a title: the type's icon with a short "In VS Code öffnen" label. It used to
 * be the icon alone, which named its action only in a tooltip. No room for a
 * stage bar, so the state goes in the tooltip, but an unusable type is still
 * visibly out of reach rather than a click that fails.
 */
export function TemplateIconButton({
  option,
  onClick,
  busy = false,
  dimmed = false,
}: {
  option: TemplateOption;
  onClick?: () => void;
  busy?: boolean;
  /** Another type on the same row is launching. */
  dimmed?: boolean;
}) {
  const de = useUiLanguage() === 'de';
  const usable = isUsable(option);
  const label = templateLabel(option);
  const state = availabilityLabel(option, de ? 'de' : 'en');
  const launch = de ? `In ${label} öffnen` : `Open in ${label}`;

  return (
    <button
      type="button"
      disabled={!usable || busy}
      title={usable ? undefined : `${label} — ${state}`}
      aria-label={usable ? undefined : `${label} — ${state}`}
      onClick={(event) => {
        // The course card wraps this row in a link; keep the click local.
        event.stopPropagation();
        onClick?.();
      }}
      className={`inline-flex items-center gap-2 rounded-lg border border-rule bg-surface pr-3 text-sm font-medium text-fg transition-opacity ${
        usable ? 'hover:bg-canvas' : 'cursor-not-allowed opacity-40 grayscale'
      } ${busy ? 'animate-pulse' : ''} ${dimmed && usable ? 'opacity-50' : ''}`}
    >
      <TemplateIcon template={{ icon: option.icon, name: option.name }} size="sm" />
      <span>{usable ? launch : label}</span>
    </button>
  );
}
