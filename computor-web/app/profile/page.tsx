'use client';

import { useEffect, useState } from 'react';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import { UserClient } from '@/src/generated/clients/UserClient';
import { AuthenticationClient } from '@/src/generated/clients/AuthenticationClient';
import { accountConsoleFrom } from '@/src/utils/accountConsole';
import { ProfilesClient } from '@/src/generated/clients/ProfilesClient';
import { useAuth } from '@/src/contexts/AuthContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Avatar, { rgbIntToHex } from '@/src/components/Avatar';
import { Field } from '@/src/components/FormPanel';
import { inputCls, readOnlyInputCls } from '@/src/components/ui/tokens';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import type { UserGet } from 'types/generated';
import { localeFor } from '@/src/utils/locale';

const usersClient = new UsersClient();
const profilesClient = new ProfilesClient();

const DEFAULT_AVATAR_HEX = '#2563eb';

const COPY = {
  de: {
    loadFailed: 'Profil konnte nicht geladen werden',
    saveFailed: 'Speichern fehlgeschlagen',
    breadcrumb: 'Mein Profil',
    title: 'Mein Profil',
    subtitle: 'Deine Identität und dein öffentliches Profil in Computor.',
    saved: 'Gespeichert',
    saving: 'Wird gespeichert …',
    save: 'Änderungen speichern',
    loading: 'Wird geladen …',
    joined: (date: string) => `beigetreten am ${date}`,
    firstName: 'Vorname',
    lastName: 'Nachname',
    email: 'E-Mail',
    emailHint: 'Die E-Mail-Adresse verwaltet dein Login-Anbieter. Ändern kannst du sie in seiner Kontoverwaltung, die du in den Einstellungen unter „Konto und Sicherheit“ öffnest.',
    emailHintNoConsole: 'Die E-Mail-Adresse verwaltet dein Login-Anbieter; hier lässt sie sich nicht ändern.',
    nickname: 'Spitzname',
    nicknameHint: 'Ein kurzer öffentlicher Name (Buchstaben, Ziffern, - und _).',
    bio: 'Über mich',
    website: 'Website',
    language: 'Sprache',
    languageHint: 'Automatisch bedeutet: Oberfläche und Aufgabentexte folgen deinem Browser. Fehlt ein Text in dieser Sprache, erscheint die vorhandene Fassung.',
    languageAuto: 'Automatisch (Browser)',
    avatarImage: 'Avatar-Bild-URL',
    avatarImageHint: 'HTTPS-Bild, ersetzt die farbigen Initialen.',
    avatarColor: 'Avatar-Farbe',
    avatarColorHint: 'Für die Initialen, wenn kein Bild gesetzt ist.',
  },
  en: {
    loadFailed: 'Failed to load profile',
    saveFailed: 'Save failed',
    breadcrumb: 'My profile',
    title: 'My profile',
    subtitle: 'Your identity and public profile across Computor.',
    saved: 'Saved',
    saving: 'Saving…',
    save: 'Save changes',
    loading: 'Loading…',
    joined: (date: string) => `joined ${date}`,
    firstName: 'First name',
    lastName: 'Last name',
    email: 'Email',
    emailHint: 'Email is managed by your login provider. Change it in its account console, which you open under “Account & Security” in Settings.',
    emailHintNoConsole: 'Email is managed by your login provider and cannot be changed here.',
    nickname: 'Nickname',
    nicknameHint: 'A short public handle (letters, numbers, - and _).',
    bio: 'Bio',
    website: 'Website',
    language: 'Language',
    languageHint: 'Automatic means the interface and the assignment texts follow your browser. Where a text has no version in that language, the existing one is shown.',
    languageAuto: 'Automatic (browser)',
    avatarImage: 'Avatar image URL',
    avatarImageHint: 'HTTPS image; overrides the colored initials.',
    avatarColor: 'Avatar color',
    avatarColorHint: 'Used for the initials badge when no image is set.',
  },
};

function roleLabel(role: string): string {
  return role.replace(/^_/, '').replace(/_/g, ' ');
}


const userClient = new UserClient();
const authenticationClient = new AuthenticationClient();
export default function ProfilePage() {
  const { user: authUser, isAuthenticated, isLoading: authLoading, setProfileLanguage } = useAuth();
  const language = useUiLanguage();
  const t = COPY[language];

  const [user, setUser] = useState<UserGet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasAccountConsole, setHasAccountConsole] = useState(false);
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
        const [u, providers] = await Promise.all([
          userClient.getCurrentUserEndpointUserGet({}),
          // The help names the Settings section only where Settings shows it.
          authenticationClient.listProvidersAuthProvidersGet().catch(() => null),
        ]);
        if (!cancelled) {
          hydrate(u);
          setHasAccountConsole(accountConsoleFrom(providers) !== null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : t.loadFailed);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isAuthenticated]);

  async function save() {
    if (!user) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      // Identity (name) lives on the user record.
      await usersClient.updateUsersUsersIdPatch({
        id: user.id,
        body: {
          given_name: givenName.trim() || null,
          family_name: familyName.trim() || null,
        },
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
        await profilesClient.updateProfileEndpointProfilesIdPatch({ id: user.profile.id, body: profileBody });
      } else {
        await profilesClient.createProfileEndpointProfilesPost({ body: { user_id: user.id, ...profileBody } });
      }

      // Re-read so the header + avatar reflect what was saved.
      hydrate(await userClient.getCurrentUserEndpointUserGet({}));
      setProfileLanguage(languageCode.trim() || null);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.saveFailed);
    } finally {
      setSaving(false);
    }
  }

  const fullName = [givenName, familyName].filter(Boolean).join(' ') || user?.email || '—';
  const previewColorInt = avatarColor ? parseInt(avatarColor.replace('#', ''), 16) : null;

  return (
    <AuthenticatedLayout>
      <ListPageLayout width="narrow">
        <PageHeader
          breadcrumbs={[{ label: t.breadcrumb }]}
          title={t.title}
          subtitle={t.subtitle}
          actions={
            user ? (
              <div className="flex items-center gap-3">
                {saved && <span className="text-sm text-success-text">{t.saved}</span>}
                <button
                  type="submit"
                  form="profile-form"
                  disabled={saving}
                  className="px-4 py-2 text-sm font-medium text-on-accent bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-50"
                >
                  {saving ? t.saving : t.save}
                </button>
              </div>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        <ScrollArea>
          <div className="space-y-6">
        {loading ? (
          <div className="text-muted">{t.loading}</div>
        ) : !user ? null : (
          <>
            {/* Identity card */}
            <div className="bg-surface border border-rule rounded-lg p-6 flex items-center gap-5">
              <Avatar size="lg" name={fullName} fallback={user.email} avatarColor={previewColorInt} avatarImage={avatarImage || null} />
              <div className="min-w-0">
                <div className="text-xl font-semibold text-fg truncate">{fullName}</div>
                <div className="text-sm text-muted truncate">{user.email}</div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {(authUser?.systemRoles ?? []).map((r) => (
                    <span key={r} className="px-2 py-0.5 text-xs rounded bg-accent-wash text-accent-text">{roleLabel(r)}</span>
                  ))}
                  {user.created_at && (
                    <span className="px-2 py-0.5 text-xs rounded bg-sunken text-muted">
                      {t.joined(new Date(user.created_at).toLocaleDateString(localeFor(language)))}
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
              className="bg-surface border border-rule rounded-lg"
            >
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label={t.firstName}>
                    <input className={inputCls} value={givenName} onChange={(e) => setGivenName(e.target.value)} />
                  </Field>
                  <Field label={t.lastName}>
                    <input className={inputCls} value={familyName} onChange={(e) => setFamilyName(e.target.value)} />
                  </Field>
                </div>
                <Field label={t.email} hint={hasAccountConsole ? t.emailHint : t.emailHintNoConsole}>
                  <input className={readOnlyInputCls} value={user.email ?? ''} disabled />
                </Field>
                <Field label={t.nickname} hint={t.nicknameHint}>
                  <input className={inputCls} value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder="jdoe" />
                </Field>
                <Field label={t.bio}>
                  <textarea className={inputCls} rows={3} value={bio} onChange={(e) => setBio(e.target.value)} />
                </Field>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label={t.website}>
                    <input className={inputCls} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" />
                  </Field>
                  <Field label={t.language} hint={t.languageHint}>
                    <select className={inputCls} value={languageCode} onChange={(e) => setLanguageCode(e.target.value)}>
                      <option value="">{t.languageAuto}</option>
                      <option value="de">Deutsch</option>
                      <option value="en">English</option>
                      {languageCode !== '' && languageCode !== 'de' && languageCode !== 'en' && (
                        <option value={languageCode}>{languageCode}</option>
                      )}
                    </select>
                  </Field>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label={t.avatarImage} hint={t.avatarImageHint}>
                    <input className={inputCls} value={avatarImage} onChange={(e) => setAvatarImage(e.target.value)} placeholder="https://…" />
                  </Field>
                  <Field label={t.avatarColor} hint={t.avatarColorHint}>
                    <input
                      type="color"
                      className="h-10 w-16 border border-rule-strong rounded cursor-pointer"
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
