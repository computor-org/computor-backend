import { NextResponse, type NextRequest } from 'next/server';
import { DOCUMENT_LANGUAGE_HEADER, fixedDocumentLanguage } from '@/src/utils/requestLanguage';

/**
 * Tells the root layout the language of a page whose text has one fixed
 * language, so <html lang> is right in the server render and not only after
 * hydration. The layout cannot see the path itself.
 */
export function proxy(request: NextRequest) {
  const language = fixedDocumentLanguage(request.nextUrl.pathname);
  const headers = new Headers(request.headers);
  if (language) headers.set(DOCUMENT_LANGUAGE_HEADER, language);
  else headers.delete(DOCUMENT_LANGUAGE_HEADER);
  return NextResponse.next({ request: { headers } });
}

export const config = {
  matcher: ['/privacy/de', '/privacy/en', '/terms/de', '/terms/en', '/terms/changes', '/terms/en/changes'],
};
