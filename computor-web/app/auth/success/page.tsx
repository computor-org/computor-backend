import { headers } from 'next/headers';
import AuthSuccessClient from './AuthSuccessClient';

export default async function AuthSuccessPage({ searchParams }: {
  searchParams: Promise<{ ui_locale?: string | string[] }>;
}) {
  const { ui_locale } = await searchParams;
  const browserLanguage = (await headers()).get('accept-language')?.split(',')[0].trim().toLowerCase();
  const initialLanguage = ui_locale === 'de' || ui_locale === 'en'
    ? ui_locale
    : browserLanguage?.startsWith('de') ? 'de' : 'en';
  return <AuthSuccessClient initialLanguage={initialLanguage} />;
}
