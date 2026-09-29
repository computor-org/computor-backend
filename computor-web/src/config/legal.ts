// Per-deployment legal profile (footer links and the /impressum, /privacy,
// /terms, /accessibility and /report pages).
//
// The same code runs on computor.at (public service with its own legal texts)
// and on code.tugraz.at (TU Graz internal, covered by TU Graz's own pages), and
// other self-hosted installs must not show either. NEXT_PUBLIC_LEGAL_PROFILE is
// inlined at build time, like NEXT_PUBLIC_API_URL:
//   computor-at      own pages from content/legal/*.md, footer links to them
//   tugraz-internal  footer links to TU Graz's pages, no own pages
//   none (default)   no legal links, no legal pages (404)

export type LegalProfile = 'computor-at' | 'tugraz-internal' | 'none';

export interface LegalLink {
  label: string;
  href: string;
  external: boolean;
}

function parseProfile(raw: string | undefined): LegalProfile {
  if (raw === 'computor-at' || raw === 'tugraz-internal') return raw;
  return 'none';
}

export const LEGAL_PROFILE: LegalProfile = parseProfile(process.env.NEXT_PUBLIC_LEGAL_PROFILE);

/** Whether this build serves its own legal pages (computor.at only). */
export const HAS_OWN_LEGAL_PAGES = LEGAL_PROFILE === 'computor-at';

const LINKS: Record<LegalProfile, LegalLink[]> = {
  'computor-at': [
    { label: 'Impressum', href: '/impressum', external: false },
    { label: 'Datenschutz', href: '/privacy', external: false },
    { label: 'Nutzungsbedingungen', href: '/terms', external: false },
    { label: 'Barrierefreiheit', href: '/accessibility', external: false },
    { label: 'Inhalte melden', href: '/report', external: false },
  ],
  'tugraz-internal': [
    { label: 'Impressum', href: 'https://www.tugraz.at/ueber-diese-seite/impressum/', external: true },
    {
      label: 'Datenschutz',
      href: 'https://www.tugraz.at/ueber-diese-seite/datenschutzerklaerung',
      external: true,
    },
    {
      label: 'Barrierefreiheit',
      href: 'https://www.tugraz.at/ueber-diese-seite/barrierefreiheitserklaerung',
      external: true,
    },
  ],
  none: [],
};

export const LEGAL_LINKS: LegalLink[] = LINKS[LEGAL_PROFILE];
