'use client';

/**
 * Shared spinner. The markup matches the ring that was previously copy-pasted
 * across the loading screens — use this instead of a raw class string so the
 * shape stays in one place.
 */
export type SpinnerSize = 'sm' | 'md' | 'lg';

const SIZE_CLS: Record<SpinnerSize, string> = {
  sm: 'h-5 w-5 border-b-2',
  md: 'h-8 w-8 border-b-2',
  lg: 'h-12 w-12 border-b-2',
};

export default function Spinner({
  size = 'lg',
  className = '',
  label,
}: {
  size?: SpinnerSize;
  className?: string;
  /** Screen-reader text; the ring itself carries no meaning without it. */
  label?: string;
}) {
  return (
    <span
      role="status"
      aria-live="polite"
      className={`inline-block animate-spin rounded-full border-blue-600 ${SIZE_CLS[size]} ${className}`}
    >
      <span className="sr-only">{label ?? 'Loading'}</span>
    </span>
  );
}
