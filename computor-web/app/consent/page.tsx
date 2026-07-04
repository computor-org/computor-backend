'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '@/src/contexts/AuthContext';
import { API_BASE_URL, CONSENT_REDIRECT_KEY, apiGet, apiPost } from '@/src/utils/apiClient';
import type { ConsentStatus, PolicyText } from '@/src/types/consent';

// Deliberately a standalone page (no AuthenticatedLayout): the sidebar/topbar
// fire API calls that are blocked by the consent gate, and this page must work
// for exactly those users.
export default function ConsentPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [status, setStatus] = useState<ConsentStatus | null>(null);
  const [policy, setPolicy] = useState<PolicyText | null>(null);
  const [accepted, setAccepted] = useState(false); // MUST default to false (no pre-ticked boxes)
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewMode, setReviewMode] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  const continueToApp = useCallback(() => {
    const target = sessionStorage.getItem(CONSENT_REDIRECT_KEY) || '/dashboard';
    sessionStorage.removeItem(CONSENT_REDIRECT_KEY);
    router.replace(target);
  }, [router]);

  const fetchPolicy = useCallback(async (lang?: string) => {
    const url = lang
      ? `${API_BASE_URL}/consent/policy?lang=${encodeURIComponent(lang)}`
      : `${API_BASE_URL}/consent/policy`;
    const response = await apiGet(url);
    if (!response.ok) {
      throw new Error(`Failed to load the privacy notice (status ${response.status})`);
    }
    setPolicy(await response.json());
  }, []);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;

    const review = new URLSearchParams(window.location.search).has('review');
    setReviewMode(review);

    async function init() {
      try {
        const statusResponse = await apiGet(`${API_BASE_URL}/consent/status`);
        if (!statusResponse.ok) {
          throw new Error(`Failed to load consent status (status ${statusResponse.status})`);
        }
        const statusData: ConsentStatus = await statusResponse.json();
        setStatus(statusData);

        // Nothing to consent to, or already consented and not reviewing:
        // send the user back to where they came from.
        if (!statusData.required_version || (statusData.has_consented && !review)) {
          continueToApp();
          return;
        }

        await fetchPolicy();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [authLoading, isAuthenticated, continueToApp, fetchPolicy]);

  const handleLanguageChange = async (lang: string) => {
    try {
      await fetchPolicy(lang);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    }
  };

  const handleSubmit = async () => {
    if (!accepted || !status?.required_version) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await apiPost(`${API_BASE_URL}/consent`, {
        policy_version: status.required_version,
      });
      if (response.status === 400) {
        // The policy version changed while the page was open — the backend
        // rejects the stale version. Reload the new notice for re-review.
        const statusResponse = await apiGet(`${API_BASE_URL}/consent/status`);
        if (statusResponse.ok) {
          setStatus(await statusResponse.json());
        }
        await fetchPolicy(policy?.lang);
        setAccepted(false);
        throw new Error(
          'The privacy notice was updated while you were reading it. Please review and accept the new version.'
        );
      }
      if (!response.ok) {
        throw new Error(`Failed to record consent (status ${response.status})`);
      }
      continueToApp();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setSubmitting(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Data Processing &amp; Privacy</h1>
          {status?.required_version && (
            <p className="mt-1 text-sm text-gray-500">
              Privacy notice version <span className="font-mono">{status.required_version}</span>
            </p>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {reviewMode && status?.has_consented && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-sm text-green-800">
              You accepted this privacy notice
              {status.granted_at ? ` on ${new Date(status.granted_at).toLocaleString()}` : ''}. You
              can withdraw your consent at any time in{' '}
              <a href="/settings" className="underline font-medium">Settings</a>.
            </p>
          </div>
        )}

        <div className="bg-white rounded-lg shadow border border-gray-200 p-6 space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">How we process your data</h2>
          <p className="text-gray-700">
            We process your personal data to deliver the courses (Lehrveranstaltungen) in which
            this platform is used — for example your name, e-mail address, course enrollments and
            submissions. The details are described in the privacy notice below.
          </p>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900">
              <span className="font-semibold">Cookies:</span> this platform only uses strictly
              necessary cookies for authentication (single sign-on session). These are required
              for the platform to function and do not need your consent; they are listed here for
              your information only.
            </p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow border border-gray-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Privacy notice</h2>
            {policy && policy.languages.length > 1 && (
              <div className="flex gap-2">
                {policy.languages.map((lang) => (
                  <button
                    key={lang}
                    onClick={() => handleLanguageChange(lang)}
                    className={`px-3 py-1 text-sm rounded-md border ${
                      policy.lang === lang
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    {lang.toUpperCase()}
                  </button>
                ))}
              </div>
            )}
          </div>
          {policy ? (
            <div className="max-h-96 overflow-y-auto border border-gray-200 rounded-lg p-4">
              <div className="prose prose-slate max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{policy.content}</ReactMarkdown>
              </div>
            </div>
          ) : (
            <p className="text-gray-600">The privacy notice could not be loaded.</p>
          )}
        </div>

        {!(reviewMode && status?.has_consented) && (
          <div className="bg-white rounded-lg shadow border border-gray-200 p-6 space-y-4">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={accepted}
                onChange={(e) => setAccepted(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-gray-700">
                I have read the privacy notice (version{' '}
                <span className="font-mono">{status?.required_version}</span>) and agree to the
                processing of my personal data as described in it.
              </span>
            </label>
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                You can withdraw your consent at any time in Settings.
              </p>
              <button
                onClick={handleSubmit}
                disabled={!accepted || submitting}
                className="px-6 py-2 rounded-lg font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {submitting ? 'Saving...' : 'Agree and continue'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
