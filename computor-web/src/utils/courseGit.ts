import type { UiLanguage } from '@/src/hooks/useUiLanguage';

// Words for a course's git binding where the API sends stored values ("git",
// "forgejo") or an English lock reason (business_logic/course_git.py).

const DELIVERY: Record<string, Record<UiLanguage, string>> = {
  git: { de: 'Git (Fork/Klon)', en: 'Git (fork/clone)' },
  download: { de: 'Download', en: 'Download' },
};

export function deliveryLabel(delivery: string | null | undefined, language: UiLanguage): string {
  if (!delivery) return '—';
  return DELIVERY[delivery]?.[language] ?? delivery;
}

const SERVER_TYPES: Record<string, string> = { forgejo: 'Forgejo', gitlab: 'GitLab', github: 'GitHub' };

export function gitServerTypeLabel(type: string | null | undefined): string {
  return type ? SERVER_TYPES[type.toLowerCase()] ?? type : '';
}

const GERMAN_LOCK_REASONS: Record<string, string> = {
  'Student repositories have already been provisioned for this course.':
    'Für diesen Kurs wurden bereits Repositories für Studierende angelegt.',
  'The git template has already been created for this course.':
    'Die Git-Vorlage für diesen Kurs wurde bereits angelegt.',
};

/** The server's lock reason in the reading language; an unknown one stays as sent. */
export function lockReasonText(reason: string | null | undefined, language: UiLanguage): string | null {
  if (!reason) return null;
  return language === 'de' ? GERMAN_LOCK_REASONS[reason] ?? reason : reason;
}
