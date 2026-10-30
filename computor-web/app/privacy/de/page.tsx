import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

export const metadata: Metadata = { title: 'Datenschutzerklärung · Computor' };

/** The German text for every reader, as the link from the English translation promises. */
export default function Page() {
  return (
    <LegalPage
      doc="datenschutz_de"
      lang="de"
      languages={[
        { label: 'Deutsch', href: '/privacy/de', lang: 'de', current: true },
        { label: 'English', href: '/privacy/en', lang: 'en', current: false },
      ]}
    />
  );
}
