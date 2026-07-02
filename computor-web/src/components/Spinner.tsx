'use client';

/** Shared loading indicator — one spinner instead of per-page variants. */
export default function Spinner({
  size = 'md',
  className = '',
}: {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  const sizeCls = { sm: 'h-4 w-4 border-b', md: 'h-8 w-8 border-b-2', lg: 'h-12 w-12 border-b-2' }[size];
  return (
    <span
      role="status"
      aria-label="Loading"
      className={`inline-block animate-spin rounded-full border-blue-600 ${sizeCls} ${className}`}
    />
  );
}

/** Centered full-area loading state for pages and cards. */
export function LoadingBlock({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="py-12 text-center">
      <Spinner size="lg" className="mx-auto" />
      <p className="mt-4 text-sm text-gray-500">{label}</p>
    </div>
  );
}
