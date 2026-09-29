import type { Metadata } from 'next';
import LegalPage from '@/src/components/LegalPage';

export const metadata: Metadata = { title: 'Barrierefreiheit / Accessibility · Computor' };

export default function Page() {
  return (
    <LegalPage
      doc="barrierefreiheit"
      languages={[
        { label: 'Deutsch', href: '#deutsch', lang: 'de', current: false },
        { label: 'English', href: '#english', lang: 'en', current: false },
      ]}
    />
  );
}
