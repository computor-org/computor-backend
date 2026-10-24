const NOTICE = {
  de: 'Mit den Mitteln der Förderaktion netidee finanziell unterstützt und ermöglicht.',
  en: 'Financially supported and made possible by the netidee funding programme.',
};

/**
 * Funding notice required by the netidee Fördervereinbarung (prj 8012).
 * Shown in every public footer; `compact` drops the sentence to the logo only
 * for the tight signed-in footer (the full sentence stays in the title).
 * The logo sits on its own white plate: its dark lettering would vanish on the
 * dark footer, and the funder's logo is shown unaltered rather than recoloured.
 * No hooks, so server components can use it too.
 */
export default function NetideeNotice({
  compact = false,
  language = 'de',
}: {
  compact?: boolean;
  language?: 'de' | 'en';
}) {
  return (
    <a
      href="https://www.netidee.at/computor"
      target="_blank"
      rel="noopener noreferrer"
      lang={language}
      className="flex items-center gap-2"
      title={NOTICE[language]}
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- small static SVG, as before */}
      <img
        src="/netidee_logo.svg"
        alt="netidee"
        className={`${compact ? 'h-5' : 'h-6'} w-auto rounded-sm bg-white px-1 py-0.5`}
      />
      {compact ? null : <span className="text-sm">{NOTICE[language]}</span>}
    </a>
  );
}
