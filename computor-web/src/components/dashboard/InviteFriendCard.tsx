'use client';

import { useState } from 'react';
import Panel from '@/src/components/ui/Panel';
import Badge from '@/src/components/Badge';
import Button from '@/src/components/ui/Button';
import { useResource } from '@/src/hooks/useResource';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { UserClient } from '@/src/generated/clients/UserClient';

const userClient = new UserClient();

const COPY = {
  de: {
    heading: 'Freund einladen',
    intro: 'Computor ist während der Pilotphase nur mit Einladung zugänglich. Mit jedem Link unten kann sich eine Person registrieren.',
    linkLabel: 'Einladungslink',
    copied: 'Kopiert',
    copy: 'Kopieren',
  },
  en: {
    heading: 'Invite a friend',
    intro: 'Computor is invite-only during the pilot. Each link below lets one person create an account.',
    linkLabel: 'Invite link',
    copied: 'Copied',
    copy: 'Copy',
  },
};

/**
 * "Invite a friend" — the caller's single-use referral links.
 *
 * Renders nothing unless registration is invite-only and the user has links
 * (staff get none; they use the invite admin page). The first read creates the
 * links server-side, so there is no "generate" button.
 */
export default function InviteFriendCard() {
  const { data } = useResource(() => userClient.getReferralInvitesUserReferralInvitesGet({}), []);
  const [copied, setCopied] = useState<string | null>(null);
  const t = COPY[useUiLanguage()];

  if (!data || data.registration_mode !== 'invite_only' || !data.invites?.length) return null;

  function copy(url: string) {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(url);
      setTimeout(() => setCopied(null), 2000);
    });
  }

  return (
    <section>
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h2 className="text-lg font-semibold text-fg">{t.heading}</h2>
      </div>
      <Panel padding="compact">
        <p className="text-sm text-muted mb-3">
          {t.intro}
        </p>
        <div className="space-y-2">
          {data.invites.map((invite) => {
            const open = invite.status === 'valid';
            return (
              <div key={invite.token} className="flex items-center gap-2">
                <input
                  readOnly
                  value={invite.url}
                  aria-label={t.linkLabel}
                  className="min-w-0 flex-1 text-xs font-mono bg-sunken border border-rule rounded px-2 py-1.5 text-body"
                  onFocus={(event) => event.target.select()}
                />
                {open ? (
                  <Button size="sm" variant="secondary" onClick={() => copy(invite.url)}>
                    {copied === invite.url ? t.copied : t.copy}
                  </Button>
                ) : (
                  <Badge tone="muted" pill>
                    {invite.status}
                  </Badge>
                )}
              </div>
            );
          })}
        </div>
      </Panel>
    </section>
  );
}
