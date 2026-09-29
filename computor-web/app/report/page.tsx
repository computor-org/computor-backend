import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

export const metadata: Metadata = { title: 'Inhalte melden / Report content · Computor' };

export default function Page() {
  return (
    <LegalPage
      doc="meldung_inhalte"
      languages={[
        { label: 'Deutsch', href: '#deutsch', lang: 'de', current: false },
        { label: 'English', href: '#english', lang: 'en', current: false },
      ]}
    />
  );
}
