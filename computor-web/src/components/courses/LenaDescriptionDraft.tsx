'use client';

import { useEffect, useState, type KeyboardEvent } from 'react';
import { ApiError } from '@/src/api/client';
import { CourseContentsClient } from '@/src/generated/clients/CourseContentsClient';
import type { DescriptionDraft, DescriptionDraftStatus } from '@/src/generated/types/courses';
import Button from '@/src/components/ui/Button';
import Notice from '@/src/components/ui/Notice';
import Spinner from '@/src/components/ui/Spinner';
import LunaAnswer from '@/src/components/student/LunaAnswer';
import { inputCls } from '@/src/components/ui/tokens';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const COPY = {
  de: {
    button: 'Entwurf von Lena',
    instruction: 'Zusätzliche Anweisung für Lena (optional)',
    instructionPlaceholder: 'z. B. „Erwähne, dass Woche 3 auf Woche 2 aufbaut“',
    queued: 'Lena wartet auf einen freien Platz …',
    running: 'Lena schreibt einen Entwurf aus den Aufgaben dieser Einheit …',
    hint: 'Lena ist eine KI. Prüfe den Entwurf, bevor du speicherst: Er wird erst mit „Speichern“ übernommen.',
    use: 'In die Beschreibung übernehmen',
    replace: 'Beschreibung durch diesen Entwurf ersetzen',
    discard: 'Verwerfen',
    cancel: 'Abbrechen',
    language: (code: string) => ({ de: 'Deutsch', en: 'Englisch' }[code] ?? code),
    failed: {
      too_long: 'Lenas Entwurf war zu lang für eine Beschreibung. Versuche es mit einer Anweisung wie „kürzer“ erneut.',
      invalid_output: 'Lena hat keinen brauchbaren Entwurf geliefert. Versuche es erneut.',
      model_error: 'Lena konnte gerade keinen Entwurf schreiben. Versuche es später erneut.',
    },
    lost: 'Der Entwurf ist nicht mehr verfügbar. Frage Lena erneut.',
    requestFailed: 'Lena konnte die Anfrage nicht annehmen.',
    busy: 'Lena schreibt gerade schon einen Entwurf für dich oder ist ausgelastet. Versuche es in ein paar Minuten erneut.',
    unavailable: 'Lena kann gerade keine Entwürfe schreiben. Versuche es später erneut.',
    noAssignments: 'Diese Einheit hat keine Aufgaben, aus denen Lena eine Beschreibung schreiben könnte.',
  },
  en: {
    button: 'Draft with Lena',
    instruction: 'Extra instruction for Lena (optional)',
    instructionPlaceholder: 'e.g. "mention that week 3 builds on week 2"',
    queued: 'Lena is waiting for a free slot…',
    running: 'Lena is writing a draft from the assignments in this unit…',
    hint: 'Lena is an AI. Check the draft before you save: it only becomes the description when you press Save.',
    use: 'Use as description',
    replace: 'Replace the description with this draft',
    discard: 'Discard',
    cancel: 'Cancel',
    language: (code: string) => ({ de: 'German', en: 'English' }[code] ?? code),
    failed: {
      too_long: "Lena's draft was too long for a description. Try again with an instruction such as \"shorter\".",
      invalid_output: 'Lena did not return a usable draft. Try again.',
      model_error: 'Lena could not write a draft just now. Try again later.',
    },
    lost: 'The draft is no longer available. Ask Lena again.',
    requestFailed: 'Lena could not take the request.',
    busy: 'Lena is already writing a draft for you or is busy. Try again in a few minutes.',
    unavailable: 'Lena cannot write drafts right now. Try again later.',
    noAssignments: 'This unit has no assignments Lena could describe.',
  },
};

const client = new CourseContentsClient();
const POLL_MS = 3000;
// Polls that may fail in a row (a restart, a network blip) before the draft
// counts as lost; a 404 means it is gone at once.
const MAX_POLL_FAILURES = 20;

/** The server's English detail is not shown; the status says enough. */
function requestError(cause: unknown, t: (typeof COPY)['en']): string {
  if (!(cause instanceof ApiError)) return t.requestFailed;
  if (cause.status === 429) return t.busy;
  if (cause.status === 503) return t.unavailable;
  if (cause.status === 400) return t.noAssignments;
  return t.requestFailed;
}

/**
 * Ask Lena for a draft of a unit's description, written from the unit's
 * assignments (computor-org/issues#559).
 *
 * The drafts are only shown here. "Use" puts one into the form's description
 * field; the form's own Save stores it, and Cancel throws it away. Renders
 * nothing unless the server has a Lena worker for drafts.
 */
export default function LenaDescriptionDraft({
  contentId,
  hasDescription,
  onUse,
}: {
  contentId: string;
  hasDescription: boolean;
  onUse: (description: string) => void;
}) {
  const t = COPY[useUiLanguage()];
  const [available, setAvailable] = useState(false);
  const [instruction, setInstruction] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<DescriptionDraftStatus | null>(null);
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    client
      .getDescriptionDraftAvailabilityCourseContentsDescriptionDraftsAvailabilityGet({})
      .then(({ enabled }) => { if (active) setAvailable(enabled); })
      .catch(() => { if (active) setAvailable(false); });
    return () => { active = false; };
  }, []);

  const finished = status?.state === 'done' || status?.state === 'failed';

  useEffect(() => {
    if (!jobId || finished) return;
    let active = true;
    let failures = 0;
    async function refresh() {
      try {
        const current = await client.getDescriptionDraftCourseContentsDescriptionDraftsJobIdGet({ jobId: jobId as string });
        failures = 0;
        if (active) setStatus(current);
      } catch (cause) {
        failures += 1;
        const gone = cause instanceof ApiError && cause.status === 404;
        if (active && (gone || failures >= MAX_POLL_FAILURES)) {
          setError(t.lost);
          setJobId(null);
          setStatus(null);
        }
      }
    }
    const timer = window.setInterval(() => { void refresh(); }, POLL_MS);
    return () => { active = false; window.clearInterval(timer); };
  }, [jobId, finished, t]);

  async function request() {
    if (requesting || (jobId && !finished)) return;
    setRequesting(true);
    setError('');
    setStatus(null);
    setJobId(null);
    try {
      const job = await client.requestDescriptionDraftCourseContentsContentIdDescriptionDraftPost({
        contentId,
        body: { instruction: instruction.trim() || null },
      });
      setJobId(job.id);
      setStatus({ id: job.id, state: job.state });
    } catch (cause) {
      setError(requestError(cause, t));
    } finally {
      setRequesting(false);
    }
  }

  function discard() {
    setJobId(null);
    setStatus(null);
  }

  // Frees the lecturer's one pending draft at once instead of after Lena's
  // timeout; if the call fails, the server lets the job expire.
  function cancel() {
    if (jobId) {
      void client
        .cancelDescriptionDraftCourseContentsDescriptionDraftsJobIdDelete({ jobId })
        .catch(() => undefined);
    }
    discard();
  }

  function use(draft: DescriptionDraft) {
    onUse(draft.description);
    discard();
  }

  // The instruction sits inside the edit form: Enter asks Lena instead of saving.
  function onInstructionKey(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') {
      event.preventDefault();
      void request();
    }
  }

  if (!available) return null;

  const busy = requesting || (!!jobId && !finished);
  const drafts = status?.state === 'done' ? status.drafts ?? [] : [];

  return (
    <div className="mt-2 space-y-2" data-testid="lena-description-draft">
      <div className="flex flex-wrap items-center gap-2">
        <input
          aria-label={t.instruction}
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          onKeyDown={onInstructionKey}
          placeholder={t.instructionPlaceholder}
          maxLength={1000}
          disabled={busy}
          className={`${inputCls} flex-1 min-w-48`}
        />
        <Button variant="secondary" size="sm" onClick={() => void request()} loading={busy}>
          {t.button}
        </Button>
      </div>

      {busy && (
        <div className="flex items-center gap-2 text-sm text-muted">
          <Spinner />
          <span>{status?.state === 'running' ? t.running : t.queued}</span>
          {jobId && (
            <Button variant="ghost" size="sm" onClick={cancel}>{t.cancel}</Button>
          )}
        </div>
      )}

      {error && <Notice tone="error">{error}</Notice>}
      {status?.state === 'failed' && (
        <Notice tone="error">{t.failed[status.error ?? 'model_error']}</Notice>
      )}

      {drafts.length > 0 && (
        <div className="space-y-3">
          <Notice tone="info">{t.hint}</Notice>
          {drafts.map((draft) => (
            <div key={draft.language} className="rounded-lg border border-rule bg-surface p-3 space-y-2">
              {drafts.length > 1 && (
                <div className="text-xs font-medium text-muted">{t.language(draft.language)}</div>
              )}
              <LunaAnswer answer={draft.description} />
              <div className="flex flex-wrap gap-2">
                <Button size="sm" onClick={() => use(draft)}>
                  {hasDescription ? t.replace : t.use}
                </Button>
              </div>
            </div>
          ))}
          <Button variant="ghost" size="sm" onClick={discard}>{t.discard}</Button>
        </div>
      )}
    </div>
  );
}
