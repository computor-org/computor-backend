import type { ProgressTone } from '@/src/components/ui/ProgressTrack';
import type { CoderTemplateTaskProgress } from '@/src/types/workspaces';

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
export interface TemplateTaskStage {
  percent: number;
  label: string;
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
): TemplateTaskStage {
  const { status, phase } = template;

  if (status === 'failed') {
    const where =
      phase === 'building' ? 'Image build failed'
      : phase === 'pushing' ? 'Push failed'
      : phase === 'rolling_out' ? 'Rollout failed'
      : 'Failed';
    return { percent: 100, label: where, tone: 'red', active: false, settled: true };
  }

  if (status === 'succeeded') {
    return {
      percent: 100,
      label: taskName === 'rollout_workspaces' ? 'Rolled out' : 'Version ready',
      tone: 'green',
      active: false,
      settled: true,
    };
  }

  switch (phase) {
    case 'building':
      return {
        percent: 30, label: 'Building image', tone: 'blue',
        active: status === 'running', settled: false,
      };
    case 'pushing':
      // `pending` here means the image is built and the push has not started —
      // the one point in the run where a template is genuinely between stages.
      return status === 'running'
        ? { percent: 75, label: 'Pushing template', tone: 'blue', active: true, settled: false }
        : { percent: 55, label: 'Image built', tone: 'blue', active: false, settled: false };
    case 'rolling_out':
      return {
        percent: 50, label: 'Rolling out workspaces', tone: 'blue',
        active: status === 'running', settled: false,
      };
    case 'complete':
      return { percent: 100, label: 'Done', tone: 'green', active: false, settled: true };
    default:
      return { percent: 4, label: 'Queued', tone: 'gray', active: false, settled: false };
  }
}

/** Human name for the workflow behind a task. */
export function taskLabel(taskName: string): string {
  if (taskName === 'rollout_workspaces') return 'Workspace rollout';
  if (taskName === 'build_workspace_images') return 'Image build';
  return 'Build & push';
}

/** Workflow-level phase, in words rather than snake_case. */
export function phaseLabel(phase?: string): string {
  return (phase || 'starting').replaceAll('_', ' ');
}
