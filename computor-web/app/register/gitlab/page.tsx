'use client';

import Image from 'next/image';
import { useState } from 'react';
import { OnboardingClient } from '@/src/clients/OnboardingClient';
import { useAuth } from '@/src/contexts/AuthContext';

const onboarding = new OnboardingClient();

export default function GitlabRegisterPage() {
  const { loginWithSSO } = useAuth();

  const [form, setForm] = useState({
    gitlabUrl: '',
    gitlabPat: '',
    password: '',
    confirmPassword: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<{ email: string; created: boolean } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (form.password !== form.confirmPassword) {
      setSubmitError('Passwords do not match');
      return;
    }
    if (form.password.length < 8) {
      setSubmitError('Password must be at least 8 characters');
      return;
    }

    setSubmitting(true);
    try {
      const res = await onboarding.registerViaGitlab({
        gitlab_url: form.gitlabUrl.trim(),
        gitlab_pat: form.gitlabPat.trim(),
        new_password: form.password,
      });
      // Account provisioned in Keycloak; no session is established here.
      setResult({ email: res.email, created: res.created });
    } catch (e) {
      setSubmitError(extractError(e, 'Registration failed'));
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 w-full max-w-md p-8 text-center">
          <div className="text-4xl mb-4">✅</div>
          <h1 className="text-xl font-semibold text-gray-900 mb-2">
            {result.created ? 'Account ready' : 'Password updated'}
          </h1>
          <p className="text-sm text-gray-500 mb-6">
            Sign in with <strong>{result.email}</strong> and the password you just chose.
          </p>
          <button
            onClick={() => loginWithSSO('keycloak')}
            className="w-full py-2.5 px-4 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            Continue to sign in
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 w-full max-w-md">
        <div className="p-8 pb-0">
          <div className="flex items-center gap-3 mb-6">
            <Image src="/computor_logo.png" alt="Computor" width={32} height={32} className="h-8 w-8" />
            <span className="text-lg font-semibold text-gray-900">Computor</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Set up your login</h1>
          <p className="text-sm text-gray-500 mb-2">
            Verify your identity with a GitLab Personal Access Token, then choose a password.
          </p>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6 text-xs text-blue-800 space-y-1">
            <div>Your GitLab account&apos;s email must match your Computor account.</div>
            <div>The token is used only to verify you and is <strong>never stored</strong>.</div>
            <div>Already set up but forgot your password? Submit again to reset it.</div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-8 pt-0 space-y-4">
          {submitError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{submitError}</div>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">GitLab URL *</label>
            <input
              type="url"
              required
              placeholder="https://gitlab.example.com"
              value={form.gitlabUrl}
              onChange={e => setForm(f => ({ ...f, gitlabUrl: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Personal Access Token *</label>
            <input
              type="password"
              required
              placeholder="glpat-…"
              value={form.gitlabPat}
              onChange={e => setForm(f => ({ ...f, gitlabPat: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-500">A personal token with access to read your profile (email).</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Password *</label>
            <input
              type="password"
              required
              minLength={8}
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Confirm password *</label>
            <input
              type="password"
              required
              value={form.confirmPassword}
              onChange={e => setForm(f => ({ ...f, confirmPassword: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 px-4 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 mt-2"
          >
            {submitting ? 'Verifying…' : 'Verify & set password'}
          </button>
        </form>
      </div>
    </div>
  );
}

/** FastAPI returns errors as `{ "detail": ... }`; the API client throws that text as Error.message. */
function extractError(e: unknown, fallback: string): string {
  if (e instanceof Error && e.message) {
    try {
      const parsed = JSON.parse(e.message);
      if (parsed?.detail) return typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail);
    } catch {
      return e.message;
    }
    return e.message;
  }
  return fallback;
}
