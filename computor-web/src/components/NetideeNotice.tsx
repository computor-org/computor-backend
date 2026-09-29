/**
 * Funding notice required by the netidee Fördervereinbarung (prj 8012).
 * Shown in every public footer; `compact` drops the sentence to the logo only
 * for the tight signed-in footer (the full sentence stays in the title).
 */
export default function NetideeNotice({ compact = false }: { compact?: boolean }) {
  return (
    <a
      href="https://www.netidee.at/computor"
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2"
      title="Dieses Projekt wurde mit den Mitteln der Förderaktion netidee finanziell unterstützt und ermöglicht."
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- small static SVG, as before */}
      <img src="/netidee_logo.svg" alt="netidee" className={compact ? 'h-4 w-auto' : 'h-5 w-auto'} />
      {compact ? null : (
        <span className="text-sm">
          Mit den Mitteln der Förderaktion netidee finanziell unterstützt
          und ermöglicht.
        </span>
      )}
    </a>
  );
}
