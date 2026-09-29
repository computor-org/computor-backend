import { LEGAL_LINKS } from '@/src/config/legal';

/**
 * The compact "Impressum · Datenschutz · …" line for the current legal profile.
 * Renders nothing when the profile has no links (NEXT_PUBLIC_LEGAL_PROFILE=none).
 * Plain anchors, no hooks: usable from server and client components alike.
 */
export default function LegalLinks({ className = '' }: { className?: string }) {
  if (LEGAL_LINKS.length === 0) return null;
  return (
    <nav aria-label="Rechtliches / Legal" className={className}>
      <ul className="flex flex-wrap items-center justify-center gap-x-1 gap-y-1">
        {LEGAL_LINKS.map((link, i) => (
          <li key={link.href} className="flex items-center gap-x-1">
            {i > 0 ? <span aria-hidden="true" className="text-faint">·</span> : null}
            <a
              href={link.href}
              className="hover:text-accent-text hover:underline underline-offset-2"
              {...(link.external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
            >
              {link.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
