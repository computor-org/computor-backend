'use client';

/** Profile avatar: a custom image when set, otherwise a colored initials badge.
 * `avatarColor` is the RGB integer stored on the profile (0–16777215). */

const SIZES: Record<'sm' | 'md' | 'lg', string> = {
  sm: 'h-8 w-8 text-sm',
  md: 'h-12 w-12 text-base',
  lg: 'h-20 w-20 text-2xl',
};

export function rgbIntToHex(color?: number | null): string | null {
  if (color === null || color === undefined || Number.isNaN(color)) return null;
  const clamped = Math.max(0, Math.min(0xffffff, Math.floor(color)));
  return `#${clamped.toString(16).padStart(6, '0')}`;
}

function initials(name?: string | null, fallback?: string | null): string {
  const parts = (name ?? '').trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  const fb = (fallback ?? '').trim();
  return fb ? fb.slice(0, 2).toUpperCase() : '?';
}

export default function Avatar({
  name,
  fallback,
  avatarColor,
  avatarImage,
  size = 'md',
}: {
  name?: string | null;
  fallback?: string | null;
  avatarColor?: number | null;
  avatarImage?: string | null;
  size?: 'sm' | 'md' | 'lg';
}) {
  const sizeCls = SIZES[size];
  if (avatarImage) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={avatarImage} alt={name ?? 'avatar'} className={`${sizeCls} rounded-full object-cover bg-gray-100`} />;
  }
  const bg = rgbIntToHex(avatarColor);
  return (
    <div
      className={`${sizeCls} rounded-full flex items-center justify-center text-white font-medium shrink-0 ${bg ? '' : 'bg-blue-600'}`}
      style={bg ? { backgroundColor: bg } : undefined}
    >
      {initials(name, fallback)}
    </div>
  );
}
