import type { UiLanguage } from '@/src/hooks/useUiLanguage';

/** Wording the course create and edit forms share, so the two never drift apart. */
export const STUDENT_REPO_MODES = ['managed', 'external', 'download'];

export const COURSE_FORM_COPY = {
  de: {
    modes: {
      managed: 'Verwaltet: Computor hostet das Repository',
      external: 'Extern: Studierende hosten es selbst (beliebiger Anbieter)',
      download: 'Download: ohne Git',
    } as Record<string, string>,
    description: 'Beschreibung',
    title: 'Titel',
    aiTutor: 'KI-Tutorin',
    gitServer: 'Git-Server',
    delivery: 'Bereitstellung',
    parentGroup: 'ID der übergeordneten GitLab-Gruppe',
    parentGroupHint: 'Die eigene GitLab-Gruppe des Kurses wird unter dieser Gruppe angelegt.',
    groupToken: 'GitLab-Gruppentoken',
    groupTokenHint: 'Ein Gruppen-Zugriffstoken für die übergeordnete Gruppe. Es wird verschlüsselt beim Kurs gespeichert und nie wieder angezeigt.',
    repoModes: 'Erlaubte Repository-Arten für Studierende',
    managedTemplate: 'Auf einem verwalteten Server (Forgejo oder GitLab) wird das Vorlagen-Repository des Kurses automatisch angelegt.',
  },
  en: {
    modes: {
      managed: 'Managed — we host it',
      external: 'External — student-hosted (any provider)',
      download: 'Download — no git',
    } as Record<string, string>,
    description: 'Description',
    title: 'Title',
    aiTutor: 'AI tutor',
    gitServer: 'Git server',
    delivery: 'Delivery',
    parentGroup: 'GitLab parent group id',
    parentGroupHint: 'The course’s own GitLab group is created under this parent group.',
    groupToken: 'GitLab group token',
    groupTokenHint: 'A group access token scoped to the parent group — stored encrypted on this course, never shown again.',
    repoModes: 'Allowed student-repo modes',
    managedTemplate: 'For a managed server (Forgejo or GitLab) the course template repo is created automatically.',
  },
} satisfies Record<UiLanguage, unknown>;
