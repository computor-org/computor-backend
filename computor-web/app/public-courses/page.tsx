'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { CourseList } from 'types/generated';
import { useAuth } from '@/src/contexts/AuthContext';
import { API_BASE_URL, apiGet, apiPost } from '@/src/utils/apiClient';

export default function PublicCoursesPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [courses, setCourses] = useState<CourseList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [joining, setJoining] = useState<string | null>(null);

  useEffect(() => {
    apiGet(`${API_BASE_URL}/public/courses`)
      .then(async (response) => {
        if (!response.ok) throw new Error('Could not load public courses.');
        setCourses(await response.json());
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load public courses.'))
      .finally(() => setLoading(false));
  }, []);

  async function join(courseId: string) {
    if (!isAuthenticated) {
      router.push(`/login?next=${encodeURIComponent('/public-courses')}`);
      return;
    }

    setJoining(courseId);
    setError(null);
    try {
      const response = await apiPost(`${API_BASE_URL}/courses/${courseId}/subscribe`);
      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || 'Could not join this course.');
      }
      router.push(`/courses/${courseId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not join this course.');
    } finally {
      setJoining(null);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-3">
            <Image src="/computor_logo.png" alt="Computor" width={36} height={36} className="h-9 w-9" />
            <span className="text-xl font-semibold text-gray-900">Computor</span>
          </Link>
          <Link href={isAuthenticated ? '/dashboard' : '/login'} className="text-sm font-medium text-blue-600 hover:text-blue-700">
            {isAuthenticated ? 'Dashboard' : 'Sign in'}
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="mb-8 max-w-2xl">
          <h1 className="text-3xl font-bold text-gray-900">Public courses</h1>
          <p className="mt-2 text-gray-600">Discover courses that allow students to join themselves.</p>
        </div>

        {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}
        {loading && <p className="text-gray-600">Loading courses…</p>}
        {!loading && !error && courses.length === 0 && (
          <div className="rounded-xl border-2 border-dashed border-gray-300 bg-white p-12 text-center text-gray-600">
            No public courses are available yet.
          </div>
        )}
        {!loading && courses.length > 0 && (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {courses.map((course) => (
              <article key={course.id} className="flex flex-col rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-gray-900">{course.title || 'Untitled course'}</h2>
                {course.description && <p className="mt-3 flex-1 text-sm leading-6 text-gray-600">{course.description}</p>}
                <div className="mt-6 flex items-center justify-between border-t border-gray-100 pt-4">
                  {course.language_code && <span className="text-xs uppercase text-gray-500">{course.language_code}</span>}
                  <button
                    type="button"
                    onClick={() => join(course.id)}
                    disabled={joining === course.id}
                    className="ml-auto rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {joining === course.id ? 'Joining…' : 'Join course'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
