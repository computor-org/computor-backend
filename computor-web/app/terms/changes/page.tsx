import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

export const metadata: Metadata = { title: 'Was sich ändert · Nutzungsbedingungen · Computor' };

export default function Page() {
  return (
    <LegalPage
      doc="nutzungsbedingungen_aenderungen_de"
      lang="de"
      languages={[
        { label: 'Deutsch', href: '/terms/changes', lang: 'de', current: true },
        { label: 'English', href: '/terms/en/changes', lang: 'en', current: false },
      ]}
    />
  );
}
