'use client';

import Badge from '@/src/components/Badge';
import Panel from '@/src/components/ui/Panel';

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
  if (tests.length === 0) return null;

  return (
    <div className="space-y-3">
      {tests.map((test, idx) => {
        const passed = test.result === 'PASSED';
        return (
          <Panel key={test.name ?? idx} padding="none">
            <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-rule bg-canvas rounded-t-lg">
              <div className="min-w-0">
                <h4 className="text-sm font-medium text-fg truncate">{test.name ?? 'Test'}</h4>
                {test.type && <p className="text-xs text-muted">{test.type}</p>}
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-xs text-muted tabular-nums">
                  {test.summary.passed}/{test.summary.total}
                </span>
                <Badge tone={passed ? 'success' : 'error'}>{test.result ?? 'UNKNOWN'}</Badge>
              </div>
            </div>

            {test.tests && test.tests.length > 0 && (
              <ul className="divide-y divide-rule-soft">
                {test.tests.map((subtest, subIdx) => {
                  const subPassed = subtest.result === 'PASSED';
                  return (
                    <li
                      key={subtest.name ?? subIdx}
                      className="flex items-start justify-between gap-3 px-4 py-2.5"
                    >
                      <div className="min-w-0">
                        <p className="text-sm text-fg">{subtest.name ?? 'Case'}</p>
                        {/* The message is only worth the space when it explains
                            a failure; on a pass it repeats the badge. */}
                        {subtest.resultMessage && !subPassed && (
                          <p className="text-xs text-red-600 mt-1">{subtest.resultMessage}</p>
                        )}
                      </div>
                      <Badge tone={subPassed ? 'success' : 'error'} className="shrink-0">
                        {subtest.result ?? 'UNKNOWN'}
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
