'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import {
  formatEffectiveDate,
  TERMS_EFFECTIVE_FROM,
  TERMS_VERSION,
  termsNoticeDue,
} from '@/src/config/terms';

/**
 * Sign-in notice of a terms change (§ 11 of the earlier versions): one line,
 * dismissible, never blocking. Shown to accounts that predate the release until
 * a week after the effective date; dismissal is remembered in this browser.
 */
function storageKey(userId: string): string {
  return `computor.termsNotice.${TERMS_VERSION}.${userId}`;
}

function readDismissed(userId: string): boolean {
  try {
    return window.localStorage.getItem(storageKey(userId)) !== null;
  } catch {
    return false;
  }
}

const TEXT = {
  de: {
    lead: (date: string) => `Ab ${date} gelten neue Nutzungsbedingungen (Version ${TERMS_VERSION}). Du musst nichts tun.`,
    changes: 'Was sich ändert',
    privacy: 'Datenschutzerklärung 1.6',
    dismiss: 'Hinweis schließen',
    changesHref: '/terms/changes',
    privacyHref: '/privacy',
  },
  en: {
    lead: (date: string) => `New Terms of Use (version ${TERMS_VERSION}) apply from ${date}. You do not need to do anything.`,
    changes: 'What changes',
    privacy: 'Privacy notice 1.6',
    dismiss: 'Dismiss notice',
    changesHref: '/terms/en/changes',
    privacyHref: '/privacy/en',
  },
} as const;

export default function TermsNoticeBanner() {
  const { user } = useAuth();
  const language = useUiLanguage();
  // Decided after mount: the clock and localStorage exist only in the browser.
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const due = !!user && termsNoticeDue(new Date(), user.createdAt) && !readDismissed(user.id);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- browser-only inputs
    setVisible(due);
  }, [user]);

  if (!visible || !user) return null;
  const t = TEXT[language];

  const dismiss = () => {
    try {
      window.localStorage.setItem(storageKey(user.id), new Date().toISOString());
    } catch {
      // Private mode or blocked storage: the notice returns on the next visit.
    }
    setVisible(false);
  };

  return (
    <div role="note" className="bg-accent-wash border-b border-accent-line px-4 py-2 print:hidden">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-accent-text">
          {t.lead(formatEffectiveDate(TERMS_EFFECTIVE_FROM, language))}{' '}
          <a href={t.changesHref} className="underline font-medium">{t.changes}</a>
          {' · '}
          <a href={t.privacyHref} className="underline">{t.privacy}</a>
        </p>
        <button
          type="button"
          onClick={dismiss}
          aria-label={t.dismiss}
          title={t.dismiss}
          className="p-1 text-accent-text hover:opacity-70 shrink-0"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
