import type { Metadata } from 'next';
import LearningOptions, { PUBLIC_COURSES_URL } from '@/src/components/courses/LearningOptions';

export const metadata: Metadata = { title: 'Public Python courses | Computor',
  description: 'Three free bilingual Data Science with Python courses. Read without an account; practice in VS Code or Codespaces.' };

const courses = [
  { slug: 'beginner', name: 'Grundlagen / Foundations', weeks: 3, examples: 21 },
  { slug: 'intermediate', name: 'Aufbau / Intermediate', weeks: 5, examples: 31 },
  { slug: 'advanced', name: 'Vertiefung / Advanced', weeks: 4, examples: 18 },
];

export default function LearnPage() {
  return (
    <main className="container mx-auto max-w-5xl px-4 py-12">
      <h1 className="text-3xl font-bold text-fg">Data Science mit Python / Data Science with Python</h1>
      <p className="my-5 text-muted">Drei freie Kurse mit deutschen und englischen Aufgaben, Vorlagen und Eingabedaten.
        Keine Anmeldung zum Lesen nötig. / Three free courses with German and English exercises, templates and input data.
        No account is required to read them.</p>
      <div className="mb-8 grid gap-4 md:grid-cols-3">
        {courses.map(course => (
          <section key={course.slug} className="rounded-lg border border-rule bg-surface p-5">
            <h2 className="text-xl font-semibold text-fg">{course.name}</h2>
            <p className="my-3 text-muted">{course.weeks} Wochen / weeks · {course.examples} Aufgaben / exercises</p>
            <a className="text-accent-text underline" href={`${PUBLIC_COURSES_URL}/blob/main/courses/python-${course.slug}.yaml`}>
              Kursaufbau / Course structure
            </a>
          </section>
        ))}
      </div>
      <p className="mb-6 text-muted">
        <a className="text-accent-text underline" href={`${PUBLIC_COURSES_URL}/tree/main/examples/python`}>Alle Beispiele lesen / Read all examples</a>
        {' · '}<a className="text-accent-text underline" href={`${PUBLIC_COURSES_URL}/blob/main/docs/GETTING_STARTED.md`}>Anleitung / Getting started</a>
        {' · '}<a className="text-accent-text underline" href={`${PUBLIC_COURSES_URL}/blob/main/RIGHTS.md`}>Lizenzen / Licenses</a>
      </p>
      <LearningOptions />
    </main>
  );
}
