import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

// The German text applies; an English reader gets the translation with a note
// saying so. The server serves the German title and the browser swaps it.
const TITLE = { de: 'Nutzungsbedingungen · Computor', en: 'Terms of Use · Computor' };

export const metadata: Metadata = { title: TITLE.de };

export default function Page() {
  return (
    <LegalPage
      doc="nutzungsbedingungen_de"
      titles={TITLE}
      translation={{ doc: 'terms_en', germanHref: '/terms/de' }}
      languages={[
        { label: 'Deutsch', href: '/terms/de', lang: 'de', current: false },
        { label: 'English', href: '/terms/en', lang: 'en', current: false },
      ]}
    />
  );
}
