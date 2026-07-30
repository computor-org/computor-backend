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
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-3" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-gray-900">
            {taskLabel(task.task_name)} · {phaseLabel(progress?.phase)}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
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
        <ul role="list" className="divide-y divide-gray-200 rounded-md border border-gray-200 bg-white">
          {templates.map((template) => {
            const stage = templateTaskStage(template, task.task_name);
            return (
              <li key={template.key} className="px-3 py-2.5">
                <div className="flex items-center gap-3">
                  <span className="w-40 shrink-0 truncate text-sm text-gray-800" title={template.name}>
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
                      stage.tone === 'red' ? 'text-red-700'
                      : stage.tone === 'green' ? 'text-green-700'
                      : 'text-gray-500'
                    }`}
                  >
                    {stage.label}
                  </span>
                </div>
                {template.error && (
                  <p className="mt-1 text-xs text-red-700 break-words">{template.error}</p>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {task.error && <p className="text-sm text-red-700">{task.error}</p>}
    </div>
  );
}
