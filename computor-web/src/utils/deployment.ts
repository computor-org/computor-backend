// How a course content's deployment state is labelled.
//
// The lecturer list and the content detail page both answer "is this released?"
// and had drifted to different words for it. The status itself is resolved
// server-side (see business_logic/lecturer_deployment); the client only names it.

import type { Tone } from '@/src/components/ui/tones';

/** The fields any content-shaped DTO carries about its deployment. */
export interface DeployableContent {
  is_submittable?: boolean;
  has_deployment?: boolean | null;
  deployment_status?: string | null;
}

const STATUS_STYLES: Record<string, { label: string; tone: Tone }> = {
  deployed: { label: 'Deployed', tone: 'success' },
  pending: { label: 'Pending', tone: 'warning' },
  failed: { label: 'Failed', tone: 'error' },
  unassigned: { label: 'Unassigned', tone: 'muted' },
};

const GERMAN_LABELS: Record<string, string> = {
  deployed: 'Bereitgestellt',
  deploying: 'Wird bereitgestellt',
  pending: 'Ausstehend',
  failed: 'Fehlgeschlagen',
  unassigned: 'Nicht zugewiesen',
};

/** A deployment status as the badge names it (unknown statuses are shown as sent). */
export function deploymentStatusLabel(status: string, language: 'de' | 'en' = 'en'): string {
  if (language === 'de') return GERMAN_LABELS[status] ?? status;
  return STATUS_STYLES[status]?.label ?? status;
}

export function deploymentBadge(
  content: DeployableContent,
  language: 'de' | 'en' = 'en',
): { label: string; tone: Tone } {
  const de = language === 'de';
  const status = content.deployment_status || (content.has_deployment ? 'deployed' : null);
  if (!status) {
    // A unit isn't deployable (no example of its own) — label it as such rather
    // than implying a submittable assignment is missing its example.
    if (!content.is_submittable) return { label: de ? 'Einheit' : 'Unit', tone: 'muted' };
    return { label: de ? 'Kein Beispiel' : 'No example', tone: 'muted' };
  }
  const style = STATUS_STYLES[status];
  if (de) return { label: GERMAN_LABELS[status] ?? status, tone: style?.tone ?? 'muted' };
  return style ?? { label: status, tone: 'muted' };
}
