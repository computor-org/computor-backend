import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

export const metadata: Metadata = { title: 'Nutzungsbedingungen · Computor' };

/** The German text for every reader, as the link from the English translation promises. */
export default function Page() {
  return (
    <LegalPage
      doc="nutzungsbedingungen_de"
      lang="de"
      languages={[
        { label: 'Deutsch', href: '/terms/de', lang: 'de', current: true },
        { label: 'English', href: '/terms/en', lang: 'en', current: false },
      ]}
    />
  );
}
