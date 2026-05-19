'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { PublicInvitesClient, InviteLinkPublic } from '@/src/generated/clients/InvitesClient';

const client = new PublicInvitesClient();
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function InvitePage() {
  const { token } = useParams<{ token: string }>();
  const router = useRouter();

  const [invite, setInvite] = useState<InviteLinkPublic | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [form, setForm] = useState({
    username: '',
    givenName: '',
    familyName: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    client.getInvitePublic(token)
      .then(data => { setInvite(data); setForm(f => ({ ...f, email: data.email ?? '' })); })
      .catch(e => setLoadError(e instanceof Error ? e.message : 'Invalid or expired invite link'))
      .finally(() => setLoading(false));
  }, [token]);

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
      const result = await client.acceptInvite(token, {
        username: form.username,
        given_name: form.givenName,
        family_name: form.familyName,
        email: form.email,
        password: form.password,
        confirm_password: form.confirmPassword,
      });

      // Cookies are now set — redirect to dashboard
      router.replace('/dashboard');
    } catch (e: any) {
      const msg = e?.response
        ? (await e.response.json().catch(() => null))?.detail ?? e.message
        : (e instanceof Error ? e.message : 'Registration failed');
      setSubmitError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading invite…</div>
      </div>
    );
  }

  if (loadError || !invite) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 w-full max-w-md p-8 text-center">
          <div className="text-4xl mb-4">🔗</div>
          <h1 className="text-xl font-semibold text-gray-900 mb-2">Invite Not Found</h1>
          <p className="text-sm text-gray-500">{loadError ?? 'This invite link is invalid or has expired.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 w-full max-w-md">
        {/* Header */}
        <div className="p-8 pb-0">
          <div className="flex items-center gap-3 mb-6">
            <img src="/computor_logo.png" alt="Computor" className="h-8 w-8" />
            <span className="text-lg font-semibold text-gray-900">Computor</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Create your account</h1>
          <p className="text-sm text-gray-500 mb-2">You've been invited to join Computor.</p>

          {/* Invite metadata */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6 text-xs text-blue-800 space-y-1">
            <div>Expires: <strong>{formatDate(invite.expires_at)}</strong></div>
            {invite.email && <div>This invite is restricted to <strong>{invite.email}</strong></div>}
            {invite.roles.length > 0 && (
              <div>Roles granted: <strong>{invite.roles.join(', ')}</strong></div>
            )}
            {invite.note && <div>Note: {invite.note}</div>}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-8 pt-0 space-y-4">
          {submitError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{submitError}</div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">First name *</label>
              <input
                type="text"
                required
                value={form.givenName}
                onChange={e => setForm(f => ({ ...f, givenName: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Last name *</label>
              <input
                type="text"
                required
                value={form.familyName}
                onChange={e => setForm(f => ({ ...f, familyName: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Email *</label>
            <input
              type="email"
              required
              value={form.email}
              readOnly={!!invite.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              className={`w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent ${invite.email ? 'bg-gray-50 cursor-not-allowed' : ''}`}
            />
            {invite.email && <p className="mt-1 text-xs text-gray-500">Email is fixed by the invite restriction.</p>}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Username *</label>
            <input
              type="text"
              required
              pattern="[a-zA-Z0-9_\-\.]+"
              value={form.username}
              onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
              placeholder="Letters, digits, _ - ."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
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
            {submitting ? 'Creating account…' : 'Create account & sign in'}
          </button>
        </form>
      </div>
    </div>
  );
}
