'use client';

import { useEffect, useState } from 'react';
import { api } from '@/src/utils/api';
import { useAuth } from '@/src/contexts/AuthContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Avatar, { rgbIntToHex } from '@/src/components/Avatar';
import { Field, inputCls } from '@/src/components/FormPanel';
import type { UserGet, ProfileGet } from 'types/generated';

const DEFAULT_AVATAR_HEX = '#2563eb';

function roleLabel(role: string): string {
  return role.replace(/^_/, '').replace(/_/g, ' ');
}

export default function ProfilePage() {
  const { user: authUser, isAuthenticated, isLoading: authLoading } = useAuth();

  const [user, setUser] = useState<UserGet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Editable fields
  const [givenName, setGivenName] = useState('');
  const [familyName, setFamilyName] = useState('');
  const [nickname, setNickname] = useState('');
  const [bio, setBio] = useState('');
  const [url, setUrl] = useState('');
  const [languageCode, setLanguageCode] = useState('');
  const [avatarImage, setAvatarImage] = useState('');
  const [avatarColor, setAvatarColor] = useState(DEFAULT_AVATAR_HEX);

  function hydrate(u: UserGet) {
    setUser(u);
    setGivenName(u.given_name ?? '');
    setFamilyName(u.family_name ?? '');
    const p = u.profile;
    setNickname(p?.nickname ?? '');
    setBio(p?.bio ?? '');
    setUrl(p?.url ?? '');
    setLanguageCode(p?.language_code ?? '');
    setAvatarImage(p?.avatar_image ?? '');
    setAvatarColor(rgbIntToHex(p?.avatar_color) ?? DEFAULT_AVATAR_HEX);
  }

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const u = await api.get<UserGet>('/user');
        if (!cancelled) hydrate(u);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load profile');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, isAuthenticated]);

  async function save() {
    if (!user) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      // Identity (name) lives on the user record.
      await api.patch<UserGet>(`/users/${user.id}`, {
        given_name: givenName.trim() || null,
        family_name: familyName.trim() || null,
      });

      // Profile fields — patch the existing profile or create one on first save.
      const colorInt = avatarColor ? parseInt(avatarColor.replace('#', ''), 16) : null;
      const profileBody = {
        nickname: nickname.trim() || null,
        bio: bio.trim() || null,
        url: url.trim() || null,
        language_code: languageCode.trim() || null,
        avatar_image: avatarImage.trim() || null,
        avatar_color: colorInt === null || Number.isNaN(colorInt) ? null : colorInt,
      };
      if (user.profile) {
        await api.patch<ProfileGet>(`/profiles/${user.profile.id}`, profileBody);
      } else {
        await api.post<ProfileGet>('/profiles', { user_id: user.id, ...profileBody });
      }

      // Re-read so the header + avatar reflect what was saved.
      hydrate(await api.get<UserGet>('/user'));
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  const fullName = [givenName, familyName].filter(Boolean).join(' ') || user?.email || '—';
  const previewColorInt = avatarColor ? parseInt(avatarColor.replace('#', ''), 16) : null;

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'My Profile' }]}
          title="My Profile"
          subtitle="Your identity and public profile across Computor."
          actions={
            user ? (
              <div className="flex items-center gap-3">
                {saved && <span className="text-sm text-green-600">Saved</span>}
                <button
                  type="submit"
                  form="profile-form"
                  disabled={saving}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Saving…' : 'Save changes'}
                </button>
              </div>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        <ScrollArea>
          <div className="max-w-3xl space-y-6">
        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : !user ? null : (
          <>
            {/* Identity card */}
            <div className="bg-white border border-gray-200 rounded-lg p-6 flex items-center gap-5">
              <Avatar size="lg" name={fullName} fallback={user.email} avatarColor={previewColorInt} avatarImage={avatarImage || null} />
              <div className="min-w-0">
                <div className="text-xl font-semibold text-gray-900 truncate">{fullName}</div>
                <div className="text-sm text-gray-500 truncate">{user.email}</div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {(authUser?.systemRoles ?? []).map((r) => (
                    <span key={r} className="px-2 py-0.5 text-xs rounded bg-blue-50 text-blue-700">{roleLabel(r)}</span>
                  ))}
                  {user.created_at && (
                    <span className="px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-500">
                      joined {new Date(user.created_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Edit form */}
            <form
              id="profile-form"
              onSubmit={(e) => {
                e.preventDefault();
                save();
              }}
              className="bg-white border border-gray-200 rounded-lg"
            >
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="First name">
                    <input className={inputCls} value={givenName} onChange={(e) => setGivenName(e.target.value)} />
                  </Field>
                  <Field label="Last name">
                    <input className={inputCls} value={familyName} onChange={(e) => setFamilyName(e.target.value)} />
                  </Field>
                </div>
                <Field label="Email" hint="Email is managed by your login provider — change it under Account & Security in Settings.">
                  <input className={`${inputCls} bg-gray-50 text-gray-500`} value={user.email ?? ''} disabled />
                </Field>
                <Field label="Nickname" hint="A short public handle (letters, numbers, - and _).">
                  <input className={inputCls} value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder="jdoe" />
                </Field>
                <Field label="Bio">
                  <textarea className={inputCls} rows={3} value={bio} onChange={(e) => setBio(e.target.value)} />
                </Field>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Website">
                    <input className={inputCls} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" />
                  </Field>
                  <Field label="Language" hint="ISO 639-1 code, e.g. en, de.">
                    <input className={inputCls} value={languageCode} onChange={(e) => setLanguageCode(e.target.value)} placeholder="en" maxLength={2} />
                  </Field>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Avatar image URL" hint="HTTPS image; overrides the colored initials.">
                    <input className={inputCls} value={avatarImage} onChange={(e) => setAvatarImage(e.target.value)} placeholder="https://…" />
                  </Field>
                  <Field label="Avatar color" hint="Used for the initials badge when no image is set.">
                    <input
                      type="color"
                      className="h-10 w-16 border border-gray-300 rounded cursor-pointer"
                      value={avatarColor}
                      onChange={(e) => setAvatarColor(e.target.value)}
                    />
                  </Field>
                </div>
              </div>
            </form>
          </>
        )}
          </div>
        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
