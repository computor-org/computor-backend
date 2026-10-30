import { test, expect } from '@playwright/test';
import { subtestMessage, testTypeLabel } from '../src/components/student/TestResultTree';

/**
 * Stored test feedback in the reader's language: the runner stores each
 * message in German and English next to the one in the language the run was
 * started in; results stored before that show their one message.
 */

const stored = {
  resultMessage: 'Fehlgeschlagen: Die Variable `x_start` wurde in deiner Lösung nicht gefunden',
  resultMessageI18n: {
    de: 'Fehlgeschlagen: Die Variable `x_start` wurde in deiner Lösung nicht gefunden',
    en: 'Failed: Variable `x_start` not found in student namespace',
  },
};

test('a message stored in both languages is shown in the reader\'s language', () => {
  expect(subtestMessage(stored, 'en')).toBe('Failed: Variable `x_start` not found in student namespace');
  expect(subtestMessage(stored, 'de')).toBe(stored.resultMessage);
});

test('an older result without translations is shown as stored', () => {
  expect(subtestMessage({ resultMessage: stored.resultMessage }, 'en')).toBe(stored.resultMessage);
  expect(subtestMessage({ resultMessage: 'x', resultMessageI18n: { de: 'y' } }, 'en')).toBe('x');
  expect(subtestMessage({}, 'de')).toBeUndefined();
});

test('test types are named in the reader\'s language', () => {
  expect(testTypeLabel('variable', 'de')).toBe('Variablen');
  expect(testTypeLabel('structural', 'de')).toBe('Struktur');
  expect(testTypeLabel('graphics', 'en')).toBe('Graphics');
  expect(testTypeLabel('someday', 'de')).toBe('someday');
});
