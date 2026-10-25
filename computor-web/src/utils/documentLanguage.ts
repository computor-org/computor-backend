/**
 * The site title in each interface language. The root layout serves the German
 * one (German first, like the server render of the public pages); the pages
 * switch it together with <html lang> once they know the visitor's language.
 */
export const APP_TITLES = {
  de: 'Computor – Lernplattform für Programmierung',
  en: 'Computor – Learning platform for programming',
} as const;

type Language = keyof typeof APP_TITLES;

let wanted: Language | null = null;
let observer: MutationObserver | null = null;

function isGenericTitle(title: string): boolean {
  return (Object.values(APP_TITLES) as string[]).includes(title);
}

function retitle(): void {
  if (wanted && isGenericTitle(document.title) && document.title !== APP_TITLES[wanted]) {
    document.title = APP_TITLES[wanted];
  }
}

/**
 * Set <html lang> and, while the tab still carries the generic site title, that
 * title in the same language. A page that set a title of its own keeps it.
 *
 * Setting document.title once is not enough: Next re-applies the root
 * metadata's <title> after hydration, which put the German title back on
 * English pages. A small observer on <head> keeps the generic title in the
 * interface language whenever it is written again.
 */
export function applyDocumentLanguage(language: Language): void {
  document.documentElement.lang = language;
  wanted = language;
  retitle();
  if (!observer) {
    observer = new MutationObserver(retitle);
    observer.observe(document.head, { subtree: true, childList: true, characterData: true });
  }
}
