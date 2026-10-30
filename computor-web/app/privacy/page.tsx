import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

// The German text applies; an English reader gets the translation with a note
// saying so. The server serves the German title and the browser swaps it.
const TITLE = { de: 'Datenschutzerklärung · Computor', en: 'Privacy notice · Computor' };

export const metadata: Metadata = { title: TITLE.de };

export default function Page() {
  return (
    <LegalPage
      doc="datenschutz_de"
      titles={TITLE}
      translation={{ doc: 'privacy_en', germanHref: '/privacy/de' }}
      languages={[
        { label: 'Deutsch', href: '/privacy/de', lang: 'de', current: false },
        { label: 'English', href: '/privacy/en', lang: 'en', current: false },
      ]}
    />
  );
}
