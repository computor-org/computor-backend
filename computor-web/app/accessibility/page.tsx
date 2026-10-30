import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

// The page holds both languages; the server serves the German title and the
// browser swaps in the English one with the section it puts in front.
const TITLE = { de: 'Barrierefreiheit · Computor', en: 'Accessibility · Computor' };

const HEADING = { de: 'Barrierefreiheitserklärung computor.at', en: 'Accessibility statement computor.at' };

export const metadata: Metadata = { title: TITLE.de };

export default function Page() {
  return (
    <LegalPage
      doc="barrierefreiheit"
      titles={TITLE}
      headings={HEADING}
      languages={[
        { label: 'Deutsch', href: '#deutsch', lang: 'de', current: false },
        { label: 'English', href: '#english', lang: 'en', current: false },
      ]}
    />
  );
}
