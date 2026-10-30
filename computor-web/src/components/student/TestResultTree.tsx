'use client';

import Badge from '@/src/components/Badge';
import Panel from '@/src/components/ui/Panel';
import { useUiLanguage, type UiLanguage } from '@/src/hooks/useUiLanguage';
import { localizedText } from '@/src/utils/localizedText';

const COPY = {
  de: { test: 'Test', case: 'Fall', unknown: 'UNBEKANNT' },
  en: { test: 'Test', case: 'Case', unknown: 'UNKNOWN' },
};

const RESULT_DE: Record<string, string> = {
  PASSED: 'BESTANDEN',
  FAILED: 'NICHT BESTANDEN',
  SKIPPED: 'ÜBERSPRUNGEN',
  ERROR: 'FEHLER',
};

/** The badge text for a tester result: the tester's own word in English, translated in German. */
export function testResultLabel(result: string | null | undefined, language: UiLanguage): string {
  if (!result) return COPY[language].unknown;
  return language === 'de' ? (RESULT_DE[result] ?? result) : result;
}

// The tester's test types (computor_types.testing.TypeEnum), as readers name them.
const TEST_TYPE: Record<string, { de: string; en: string }> = {
  variable: { de: 'Variablen', en: 'Variables' },
  graphics: { de: 'Grafik', en: 'Graphics' },
  structural: { de: 'Struktur', en: 'Structure' },
  linting: { de: 'Stil', en: 'Style' },
  exist: { de: 'Dateien', en: 'Files' },
  error: { de: 'Fehler', en: 'Errors' },
  warning: { de: 'Warnungen', en: 'Warnings' },
  help: { de: 'Hilfetext', en: 'Help text' },
  stdout: { de: 'Ausgabe', en: 'Output' },
  stderr: { de: 'Fehlerausgabe', en: 'Error output' },
  stdio: { de: 'Ein- und Ausgabe', en: 'Input and output' },
  exitcode: { de: 'Exit-Code', en: 'Exit code' },
  compile: { de: 'Kompilierung', en: 'Compilation' },
  runtime: { de: 'Laufzeit', en: 'Runtime' },
  wordcount: { de: 'Wortzahl', en: 'Word count' },
  paragraphcount: { de: 'Absatzzahl', en: 'Paragraph count' },
  section: { de: 'Abschnitte', en: 'Sections' },
  linkcount: { de: 'Links', en: 'Links' },
  keyword: { de: 'Schlüsselwörter', en: 'Keywords' },
  uniquewords: { de: 'Verschiedene Wörter', en: 'Distinct words' },
};

/** A test collection's type in the reader's language; an unknown type as the tester wrote it. */
export function testTypeLabel(type: string, language: UiLanguage): string {
  return TEST_TYPE[type]?.[language] ?? type;
}

/**
 * A subtest's message in the reader's language. Newer runners store every
 * message per language next to the one in the language the run was started in;
 * older results have only that one and are shown as stored.
 */
export function subtestMessage(subtest: SubtestResult, language: UiLanguage): string | undefined {
  return localizedText(subtest.resultMessageI18n, language, subtest.resultMessage);
}

/**
 * The tester's `result_json` payload. Not covered by the generated types — the
 * backend stores it as opaque JSON — so the shape is declared here, once, rather
 * than re-declared by each page that reads it.
 */
export interface TestSummary {
  passed: number;
  failed: number;
  skipped: number;
  total: number;
}

export interface SubtestResult {
  name?: string;
  result?: string;
  resultMessage?: string;
  resultMessageI18n?: Record<string, string> | null;
}

export interface TestResult {
  name?: string;
  type?: string;
  result?: string;
  summary: TestSummary;
  tests?: SubtestResult[];
}

export interface TestRunResult {
  result?: string;
  result_value?: number;
  summary: TestSummary;
  tests?: TestResult[];
}

/**
 * A test run's per-test breakdown.
 *
 * Pass/fail used to be drawn with literal ✓ and ✗ characters — which render at
 * whatever weight the font decides, carry no accessible name, and sat next to
 * <Badge>es saying the same thing in a different visual language two lines up.
 * A badge is the app's word for "state of a thing"; this uses it throughout.
 */
export default function TestResultTree({ tests }: { tests: TestResult[] }) {
  const language = useUiLanguage();
  const t = COPY[language];
  if (tests.length === 0) return null;

  return (
    <div className="space-y-3">
      {tests.map((test, idx) => {
        const passed = test.result === 'PASSED';
        return (
          <Panel key={test.name ?? idx} padding="none">
            <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-rule bg-canvas rounded-t-lg">
              <div className="min-w-0">
                <h4 className="text-sm font-medium text-fg truncate">{test.name ?? t.test}</h4>
                {test.type && <p className="text-xs text-muted">{testTypeLabel(test.type, language)}</p>}
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-xs text-muted tabular-nums">
                  {test.summary.passed}/{test.summary.total}
                </span>
                <Badge tone={passed ? 'success' : 'error'}>{testResultLabel(test.result, language)}</Badge>
              </div>
            </div>

            {test.tests && test.tests.length > 0 && (
              <ul className="divide-y divide-rule-soft">
                {test.tests.map((subtest, subIdx) => {
                  const subPassed = subtest.result === 'PASSED';
                  const message = subtestMessage(subtest, language);
                  return (
                    <li
                      key={subtest.name ?? subIdx}
                      className="flex items-start justify-between gap-3 px-4 py-2.5"
                    >
                      <div className="min-w-0">
                        <p className="text-sm text-fg">{subtest.name ?? t.case}</p>
                        {/* The message is only worth the space when it explains
                            a failure; on a pass it repeats the badge. */}
                        {message && !subPassed && (
                          <p className="text-xs text-danger-text mt-1 whitespace-pre-line">{message}</p>
                        )}
                      </div>
                      <Badge tone={subPassed ? 'success' : 'error'} className="shrink-0">
                        {testResultLabel(subtest.result, language)}
                      </Badge>
                    </li>
                  );
                })}
              </ul>
            )}
          </Panel>
        );
      })}
    </div>
  );
}
