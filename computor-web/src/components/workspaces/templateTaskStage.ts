import type { ProgressTone } from '@/src/components/ui/ProgressTrack';
import type { CoderTemplateTaskProgress } from '@/src/types/workspaces';
import type { UiLanguage } from '@/src/hooks/useUiLanguage';

const COPY = {
  de: {
    imageBuildFailed: 'Image-Build fehlgeschlagen',
    pushFailed: 'Push fehlgeschlagen',
    rolloutFailed: 'Rollout fehlgeschlagen',
    failed: 'Fehlgeschlagen',
    rolledOut: 'Ausgerollt',
    versionReady: 'Version bereit',
    buildingImage: 'Image wird gebaut',
    pushingTemplate: 'Vorlage wird gepusht',
    imageBuilt: 'Image gebaut',
    rollingOut: 'Arbeitsumgebungen werden ausgerollt',
    done: 'Fertig',
    queued: 'In Warteschlange',
    workspaceRollout: 'Rollout der Arbeitsumgebungen',
    imageBuild: 'Image-Build',
    buildPush: 'Build & Push',
    starting: 'startet',
    phases: {
      queued: 'in Warteschlange',
      building: 'Build läuft',
      pushing: 'Push läuft',
      rolling_out: 'Rollout läuft',
      complete: 'abgeschlossen',
    } as Record<string, string>,
  },
  en: {
    imageBuildFailed: 'Image build failed',
    pushFailed: 'Push failed',
    rolloutFailed: 'Rollout failed',
    failed: 'Failed',
    rolledOut: 'Rolled out',
    versionReady: 'Version ready',
    buildingImage: 'Building image',
    pushingTemplate: 'Pushing template',
    imageBuilt: 'Image built',
    rollingOut: 'Rolling out workspaces',
    done: 'Done',
    queued: 'Queued',
    workspaceRollout: 'Workspace rollout',
    imageBuild: 'Image build',
    buildPush: 'Build & push',
    starting: 'starting',
    phases: {} as Record<string, string>,
  },
};

/**
 * Where one template is in a build / push / rollout run, as something a bar can
 * draw.
 *
 * The workflow reports a (status, phase) pair per template — the phases are
 * `queued`, `building`, `pushing`, `rolling_out`, `complete` (see
 * tasks/temporal_coder_setup.py). The percentages below are those stage
 * boundaries: an image build is the long pole, so reaching "image built" is
 * more than halfway even though it is one step of two.
 */
export type StageKey =
  | 'imageBuildFailed' | 'pushFailed' | 'rolloutFailed' | 'failed' | 'rolledOut'
  | 'versionReady' | 'buildingImage' | 'pushingTemplate' | 'imageBuilt'
  | 'rollingOut' | 'done' | 'queued';

/** The stage's label in the given language. */
export function stageLabel(key: StageKey, language: UiLanguage = 'en'): string {
  return COPY[language][key];
}

export interface TemplateTaskStage {
  percent: number;
  label: string;
  /** Which stage this is, so a label can be re-rendered in another language. */
  key: StageKey;
  tone: ProgressTone;
  /** Still moving — the bar sweeps rather than sitting still. */
  active: boolean;
  /**
   * This template is done with, one way or the other. Callers draw no bar for
   * it: a full bar reports the same thing its label already does, and a
   * finished run would otherwise leave a row of them sitting there for good.
   */
  settled: boolean;
}

export function templateTaskStage(
  /** Anything carrying the workflow's (status, phase) pair — a progress entry
      from the admin task feed, or a TemplatePreparation from the user-facing
      template listing. */
  template: Pick<CoderTemplateTaskProgress, 'status' | 'phase'>,
  /** Which workflow this is: a rollout's single phase reads differently. */
  taskName?: string,
  language: UiLanguage = 'en',
): TemplateTaskStage {
  const { status, phase } = template;
  const t = COPY[language];

  if (status === 'failed') {
    const key: StageKey =
      phase === 'building' ? 'imageBuildFailed'
      : phase === 'pushing' ? 'pushFailed'
      : phase === 'rolling_out' ? 'rolloutFailed'
      : 'failed';
    return { percent: 100, label: t[key], key, tone: 'red', active: false, settled: true };
  }

  if (status === 'succeeded') {
    return {
      percent: 100,
      label: taskName === 'rollout_workspaces' ? t.rolledOut : t.versionReady,
      key: taskName === 'rollout_workspaces' ? 'rolledOut' : 'versionReady',
      tone: 'green',
      active: false,
      settled: true,
    };
  }

  switch (phase) {
    case 'building':
      return {
        percent: 30, label: t.buildingImage, key: 'buildingImage', tone: 'blue',
        active: status === 'running', settled: false,
      };
    case 'pushing':
      // `pending` here means the image is built and the push has not started —
      // the one point in the run where a template is genuinely between stages.
      return status === 'running'
        ? { percent: 75, label: t.pushingTemplate, key: 'pushingTemplate', tone: 'blue', active: true, settled: false }
        : { percent: 55, label: t.imageBuilt, key: 'imageBuilt', tone: 'blue', active: false, settled: false };
    case 'rolling_out':
      return {
        percent: 50, label: t.rollingOut, key: 'rollingOut', tone: 'blue',
        active: status === 'running', settled: false,
      };
    case 'complete':
      return { percent: 100, label: t.done, key: 'done', tone: 'green', active: false, settled: true };
    default:
      return { percent: 4, label: t.queued, key: 'queued', tone: 'gray', active: false, settled: false };
  }
}

/** Human name for the workflow behind a task. */
export function taskLabel(taskName: string, language: UiLanguage = 'en'): string {
  const t = COPY[language];
  if (taskName === 'rollout_workspaces') return t.workspaceRollout;
  if (taskName === 'build_workspace_images') return t.imageBuild;
  return t.buildPush;
}

/** Workflow-level phase, in words rather than snake_case. */
export function phaseLabel(phase?: string, language: UiLanguage = 'en'): string {
  const t = COPY[language];
  if (!phase) return t.starting;
  return t.phases[phase] ?? phase.replaceAll('_', ' ');
}
