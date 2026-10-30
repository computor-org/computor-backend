import { test, expect } from '@playwright/test';
import JSZip from 'jszip';
import {
  descriptionHeading,
  localizedUnitTitle,
  pickDescriptionFile,
  plainHeading,
  readStudentDescription,
  withoutLeadingHeading,
} from '../src/components/student/studentDescription';

async function archive(files: Record<string, string>): Promise<ArrayBuffer> {
  const zip = new JSZip();
  for (const [name, contents] of Object.entries(files)) zip.file(name, contents);
  return zip.generateAsync({ type: 'arraybuffer' });
}

test('a German reader gets the German README, not the English one', async () => {
  const zip = await archive({
    'index_en.md': '# Mathematical Constants\n\nThis is the first task.',
    'index_de.md': '[NumPy]: <https://numpy.org/>\n\n# Mathematische Konstanten\n\nDies ist die erste Aufgabe.',
    'mediaFiles/plot.png': 'png',
  });
  const description = await readStudentDescription(zip, 'de');
  expect(descriptionHeading(description?.markdown)).toBe('Mathematische Konstanten');
  expect(withoutLeadingHeading(description!.markdown)).not.toContain('Mathematische Konstanten');
  expect(withoutLeadingHeading(description!.markdown)).toContain('Dies ist die erste Aufgabe.');
  expect(Object.keys(description!.images)).toEqual(['mediaFiles/plot.png']);
});

test('without the preferred language: English, then the default document', () => {
  expect(pickDescriptionFile(['README.md', 'README_en.md'], 'fr')).toBe('README_en.md');
  expect(pickDescriptionFile(['README.md', 'README_de.md'], 'fr')).toBe('README.md');
  expect(pickDescriptionFile(['main.py'], 'de')).toBeUndefined();
});

test('titles: plain headings and week units in the reading language', () => {
  expect(plainHeading('Approximation von $\\pi$ mit *Reihen*')).toBe('Approximation von π mit Reihen');
  expect(localizedUnitTitle('Week 2', 'de')).toBe('Woche 2');
  expect(localizedUnitTitle('Woche 2', 'en')).toBe('Week 2');
});
