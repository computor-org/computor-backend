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
/**
 * Titles of a page that holds both languages on one page, which therefore calls
 * itself by its title in the reading language. Null on the pages that carry the
 * generic site title.
 */
let ownTitles: Record<Language, string> | null = null;

function isGenericTitle(title: string): boolean {
  return (Object.values(APP_TITLES) as string[]).includes(title);
}

function retitle(): void {
  if (!wanted) return;
  const titles = ownTitles ?? APP_TITLES;
  // A page that chose a title of its own keeps it, unless it asked for a pair.
  if (!ownTitles && !isGenericTitle(document.title)) return;
  if (document.title !== titles[wanted]) document.title = titles[wanted];
}

/**
 * Set <html lang> and, while the tab still carries the generic site title, that
 * title in the same language. A page that set a title of its own keeps it.
 *
 * Setting document.title once is not enough: Next re-applies the root
 * metadata's <title> after hydration, which put the German title back on
 * English pages. A small observer on <head> keeps the generic title in the
 * interface language whenever it is written again.
 *
 * `titles` is for a page written in both languages at once: it names itself in
 * whichever of the two is being read. Call the returned function on unmount so
 * the observer stops defending a title that belonged to a page since gone.
 */
export function applyDocumentLanguage(language: Language, titles?: Record<Language, string>): () => void {
  document.documentElement.lang = language;
  wanted = language;
  ownTitles = titles ?? null;
  retitle();
  if (!observer) {
    observer = new MutationObserver(retitle);
    observer.observe(document.head, { subtree: true, childList: true, characterData: true });
  }
  return () => {
    if (ownTitles === (titles ?? null)) ownTitles = null;
  };
}
