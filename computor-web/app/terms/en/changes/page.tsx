import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

export const metadata: Metadata = { title: 'What changes · Terms of Use · Computor' };

export default function Page() {
  return (
    <LegalPage
      doc="terms_changes_en"
      lang="en"
      languages={[
        { label: 'Deutsch', href: '/terms/changes', lang: 'de', current: false },
        { label: 'English', href: '/terms/en/changes', lang: 'en', current: true },
      ]}
    />
  );
}
