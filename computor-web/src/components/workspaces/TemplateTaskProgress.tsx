'use client';

import Badge from '@/src/components/Badge';
import ProgressTrack from '@/src/components/ui/ProgressTrack';
import { TaskStatus, type TaskInfo } from '@/src/types/workspaces';
import { phaseLabel, taskLabel, templateTaskStage } from './templateTaskStage';

/**
 * Live progress of one image-build / template-push / rollout run.
 *
 * A list, not a grid of cards: these are the stages of one operation running
 * over a known set of templates, so they belong in reading order with their
 * bars on a shared left edge — the point is comparing how far each has got,
 * and cards scatter that across a grid whose row wrapping changes with the
 * window width. Every template gets its own bar, plus one for the run.
 */
export default function TemplateTaskProgress({ task }: { task: TaskInfo }) {
  const progress = task.progress;
  const templates = progress?.templates ?? [];
  const total = progress?.total ?? templates.length;
  const completed = progress?.completed ?? 0;

  const failed = task.status === TaskStatus.FAILED
    || progress?.operation_status === 'completed_with_errors';
  const finished = failed || task.status === TaskStatus.FINISHED
    || progress?.operation_status === 'completed';

  return (
    <div className="rounded-lg border border-rule bg-canvas p-4 space-y-3" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-fg">
            {taskLabel(task.task_name)} · {phaseLabel(progress?.phase)}
          </p>
          <p className="text-xs text-muted mt-0.5">
            {completed} / {total} templates
            {progress?.image_tag ? ` · ${progress.image_tag}` : ''}
            {task.duration ? ` · ${task.duration}` : ''}
          </p>
        </div>
        <Badge pill color={failed ? 'red' : finished ? 'green' : 'blue'}>
          {progress?.operation_status || task.status}
        </Badge>
      </div>

      {/*
        No bar for the run itself. It measured the same templates the list
        below does, one row at a time — so it said nothing the rows did not,
        twice, in the same colour.
      */}
      {templates.length > 0 && (
        <ul role="list" className="divide-y divide-rule rounded-md border border-rule bg-surface">
          {templates.map((template) => {
            const stage = templateTaskStage(template, task.task_name);
            return (
              <li key={template.key} className="px-3 py-2.5">
                <div className="flex items-center gap-3">
                  <span className="w-40 shrink-0 truncate text-sm text-fg" title={template.name}>
                    {template.display_name || template.name}
                  </span>
                  <div className="flex-1 min-w-0">
                    {/*
                      Only while it is still going. A finished template's bar is
                      full by definition, so it reports what "Version ready"
                      already says — and once the run ends every row would keep
                      one, a wall of complete bars describing nothing in flight.
                      The column stays so the labels beside it stay aligned.
                    */}
                    {!stage.settled && (
                      <ProgressTrack
                        value={stage.percent}
                        tone={stage.tone}
                        active={stage.active}
                        label={`${template.display_name || template.name}: ${stage.label}`}
                      />
                    )}
                  </div>
                  <span
                    className={`w-40 shrink-0 text-right text-xs ${
                      stage.tone === 'red' ? 'text-danger-text'
                      : stage.tone === 'green' ? 'text-success-text'
                      : 'text-muted'
                    }`}
                  >
                    {stage.label}
                  </span>
                </div>
                {/*
                  The commit each tracked repo was built from. Without it a
                  build reports success identically whether or not it picked up
                  the change you just merged — which is exactly how stale
                  extensions used to ship unnoticed.
                */}
                {template.source_revisions && Object.keys(template.source_revisions).length > 0 && (
                  <p className="mt-1 text-xs text-muted">
                    {Object.entries(template.source_revisions).map(([arg, sha]) => (
                      <span key={arg} className="mr-3 font-mono" title={`${arg}=${sha}`}>
                        {sha.slice(0, 10)}
                      </span>
                    ))}
                  </p>
                )}
                {template.error && (
                  <p className="mt-1 text-xs text-danger-text break-words">{template.error}</p>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {task.error && <p className="text-sm text-danger-text">{task.error}</p>}
    </div>
  );
}
