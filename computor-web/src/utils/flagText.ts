/**
 * Localized text for the rule-based grading flags. The backend sends stable
 * flag `code`s plus English `title`/`reason`/`description` strings. German is
 * derived from the code, and the numbers are read back out of the backend
 * sentence. Whatever does not match a known pattern keeps the backend text,
 * so an unknown flag or a reworded rule never shows blank or wrong text.
 */

import type { UiLanguage } from '@/src/hooks/useUiLanguage';
import type { FlagReason, FlagRule } from 'types/generated';

const TITLE_DE: Record<string, string> = {
  many_failed_attempts: 'Viele fehlgeschlagene Versuche',
  sudden_jump: 'Sprung auf volle Punktzahl',
  inactive: 'Inaktiv',
  low_progress: 'Geringer Fortschritt',
  last_minute: 'Abgabe auf den letzten Drücker',
  late_submission: 'Abgabe nach der Frist',
};

const de = (n: string) => n.replace('.', ',');

export function flagTitle(code: string, fallback: string, language: UiLanguage): string {
  return language === 'de' ? (TITLE_DE[code] ?? fallback) : fallback;
}

export function flagReason(flag: Pick<FlagReason, 'code' | 'reason'>, language: UiLanguage): string {
  if (language !== 'de') return flag.reason;
  const r = flag.reason;
  let m: RegExpMatchArray | null;
  switch (flag.code) {
    case 'many_failed_attempts':
      if ((m = r.match(/^(\d+) test runs without full score( before reaching it\.|; full score not reached yet\.)$/))) {
        return `${m[1]} Testläufe ohne volle Punktzahl` +
          (m[2].startsWith(' before') ? ', bevor sie erreicht wurde.' : '; volle Punktzahl noch nicht erreicht.');
      }
      break;
    case 'sudden_jump':
      if ((m = r.match(/^From (\S+) to (\S+) between two consecutive test runs (\d+) min apart\.$/))) {
        return `Von ${m[1]} auf ${m[2]} zwischen zwei aufeinanderfolgenden Testläufen im Abstand von ${m[3]} min.`;
      }
      break;
    case 'late_submission':
      if ((m = r.match(/^(\d+) submission\(s\) after the due date; the first ([\d.]+) h late\.$/))) {
        return `${m[1]} Abgabe(n) nach der Frist, die erste ${de(m[2])} Std. zu spät.`;
      }
      break;
    case 'last_minute':
      if ((m = r.match(/^Last submission (\d+) min before the due date\.$/))) {
        return `Letzte Abgabe ${m[1]} min vor der Frist.`;
      }
      break;
    case 'inactive':
      if (r === 'No test run and no submission so far.') return 'Bisher kein Testlauf und keine Abgabe.';
      if ((m = r.match(/^Last test run or submission (\d+) days ago\.$/))) {
        return `Letzter Testlauf oder letzte Abgabe vor ${m[1]} Tagen.`;
      }
      break;
    case 'low_progress':
      if ((m = r.match(/^Submitted (\d+) of (\d+) assignments \((\d+)%\)\.$/))) {
        return `${m[1]} von ${m[2]} Aufgaben abgegeben (${m[3]} %).`;
      }
      break;
  }
  return r;
}

const DUE_NOTE_DE: Record<string, string> = {
  'Uses the due date set on the page; the platform does not store per-assignment deadlines.':
    'Es gilt die auf der Seite gesetzte Frist, denn die Plattform speichert keine Fristen je Aufgabe.',
  'Only evaluated when a due date is set on the page.': 'Wird nur ausgewertet, wenn auf der Seite eine Frist gesetzt ist.',
};

export function flagRuleDescription(rule: Pick<FlagRule, 'code' | 'description'>, language: UiLanguage): string {
  if (language !== 'de') return rule.description;
  const d = rule.description;
  let m: RegExpMatchArray | null;
  const note = (s: string) => DUE_NOTE_DE[s] ?? s;
  switch (rule.code) {
    case 'many_failed_attempts':
      if ((m = d.match(/^At least (\d+) test runs on one assignment without reaching the full score \(counted up to the first full-score run\)\.$/))) {
        return `Mindestens ${m[1]} Testläufe bei einer Aufgabe, ohne die volle Punktzahl zu erreichen (gezählt bis zum ersten Lauf mit voller Punktzahl).`;
      }
      break;
    case 'sudden_jump':
      if ((m = d.match(/^A test run reached the full score directly after a run at or below (\d+)% on the same assignment\. Worth a look; not evidence of misconduct on its own\.$/))) {
        return `Ein Testlauf erreichte die volle Punktzahl direkt nach einem Lauf mit höchstens ${m[1]} % bei derselben Aufgabe. Ein Blick lohnt sich, ein Beleg für Fehlverhalten ist das allein nicht.`;
      }
      break;
    case 'inactive':
      if ((m = d.match(/^No test run and no submission in the last (\d+) days\.$/))) {
        return `Kein Testlauf und keine Abgabe in den letzten ${m[1]} Tagen.`;
      }
      break;
    case 'low_progress':
      if ((m = d.match(/^Submitted fewer than (\d+)% of the submittable assignments\.$/))) {
        return `Weniger als ${m[1]} % der abgebbaren Aufgaben abgegeben.`;
      }
      break;
    case 'last_minute':
      if ((m = d.match(/^Last submission less than ([\d.]+) h before the due date\. (.*)$/))) {
        return `Letzte Abgabe weniger als ${de(m[1])} Std. vor der Frist. ${note(m[2])}`;
      }
      break;
    case 'late_submission':
      if ((m = d.match(/^At least one submission after the due date\. (.*)$/))) {
        return `Mindestens eine Abgabe nach der Frist. ${note(m[1])}`;
      }
      break;
  }
  return d;
}
