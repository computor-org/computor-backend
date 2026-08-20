'use client';

import { ReactNode, useEffect, useId, useRef, useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';

// "Has this hydrated yet?" without a setState-in-effect: the store never
// changes, so the answer is simply which snapshot React asks for. The server —
// and the first client render, which must match it — gets false; every render
// after hydration gets true, at which point `document` exists to portal into.
const subscribeToNothing = () => () => {};
const onClient = () => true;
const onServer = () => false;

/**
 * Accessible modal base: backdrop, dialog semantics, focus trap, Escape.
 *
 * Every dialog in the app should render through this so screen readers
 * announce it (`role="dialog"`, `aria-modal`, `aria-labelledby`) and Tab
 * cannot escape to the page behind it (WCAG 2.1 SC 2.1.2). Focus returns
 * to the previously focused element on close.
 *
 * Rendered into <body> via a portal so `position: fixed` always resolves
 * against the viewport. Several ancestors would otherwise capture it: any
 * `transform`, `filter` or — since the scroll-fade utility — `mask-image` on an
 * enclosing element makes that element the containing block for fixed
 * descendants, which would trap a dialog opened from inside a scroll area.
 */
export default function Modal({
  title,
  titleClassName = 'text-lg font-semibold text-fg',
  onClose,
  children,
  maxWidth = 'max-w-md',
}: {
  title: ReactNode;
  titleClassName?: string;
  /** Called on backdrop click and Escape. Pass a no-op to force a button choice. */
  onClose: () => void;
  children: ReactNode;
  maxWidth?: string;
}) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const mounted = useSyncExternalStore(subscribeToNothing, onClient, onServer);

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;

    const focusables = () =>
      panel.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );

    // Move focus into the dialog unless something inside (e.g. an autoFocus
    // input) already took it.
    if (!panel.contains(document.activeElement)) {
      (focusables()[0] ?? panel).focus();
    }

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== 'Tab') return;

      const items = focusables();
      if (items.length === 0) {
        e.preventDefault();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      previouslyFocused?.focus?.();
    };
    // `mounted` gates the portal, so the panel this effect needs only exists
    // once it flips true.
  }, [onClose, mounted]);

  if (!mounted) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={`relative bg-surface rounded-lg shadow-xl w-full mx-4 ${maxWidth}`}
      >
        <h2 id={titleId} className={`${titleClassName} px-6 pt-6`}>
          {title}
        </h2>
        {children}
      </div>
    </div>,
    document.body,
  );
}
