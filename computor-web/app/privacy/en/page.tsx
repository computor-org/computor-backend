import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

export const metadata: Metadata = { title: 'Privacy notice · Computor' };

export default function Page() {
  return (
    <LegalPage
      doc="privacy_en"
      lang="en"
      languages={[
        { label: 'Deutsch', href: '/privacy', lang: 'de', current: false },
        { label: 'English', href: '/privacy/en', lang: 'en', current: true },
      ]}
    />
  );
}
