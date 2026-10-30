import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

// The page holds both languages; the server serves the German title and the
// browser swaps in the English one with the section it puts in front.
const TITLE = { de: 'Impressum · Computor', en: 'Imprint · Computor' };

const HEADING = { de: 'Impressum computor.at', en: 'Imprint computor.at' };

export const metadata: Metadata = { title: TITLE.de };

export default function Page() {
  return (
    <LegalPage
      doc="impressum"
      titles={TITLE}
      headings={HEADING}
      languages={[
        { label: 'Deutsch', href: '#deutsch', lang: 'de', current: false },
        { label: 'English', href: '#english', lang: 'en', current: false },
      ]}
    />
  );
}
