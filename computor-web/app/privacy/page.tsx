import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

export const metadata: Metadata = { title: 'Datenschutzerklärung · Computor' };

export default function Page() {
  return (
    <LegalPage
      doc="datenschutz_de"
      lang="de"
      languages={[
        { label: 'Deutsch', href: '/privacy', lang: 'de', current: true },
        { label: 'English', href: '/privacy/en', lang: 'en', current: false },
      ]}
    />
  );
}
