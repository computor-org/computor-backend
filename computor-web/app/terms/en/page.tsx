import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

export const metadata: Metadata = { title: 'Terms of Use · Computor' };

export default function Page() {
  return (
    <LegalPage
      doc="terms_en"
      lang="en"
      languages={[
        { label: 'Deutsch', href: '/terms', lang: 'de', current: false },
        { label: 'English', href: '/terms/en', lang: 'en', current: true },
      ]}
    />
  );
}
