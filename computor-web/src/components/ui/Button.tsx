'use client';

import { ButtonHTMLAttributes, ReactNode } from 'react';
import Link from 'next/link';

/**
 * Shared button. The primary/danger/secondary/ghost variants match the styles
 * that were previously copy-pasted across pages — use this instead of raw
 * class strings so the palette stays in one place.
 */
export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'dangerGhost' | 'accentGhost' | 'ghost';
export type ButtonSize = 'xs' | 'sm' | 'md';

const VARIANT_CLS: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-on-accent hover:bg-accent-hover',
  secondary: 'border border-rule-strong text-body bg-surface hover:bg-canvas',
  danger: 'bg-danger text-on-accent hover:bg-danger-hover',
  // Low-emphasis destructive action (e.g. Delete in a table row) — red text
  // without the solid fill that would shout from every row.
  dangerGhost: 'text-danger-text hover:bg-danger-wash',
  // Accent twin of dangerGhost: the row's main action (Copy Link, Open) as
  // accent text without a fill.
  accentGhost: 'text-accent-text hover:bg-accent-wash',
  ghost: 'text-muted hover:bg-sunken',
};

const SIZE_CLS: Record<ButtonSize, string> = {
  xs: 'px-2.5 py-1 text-xs',
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
};

export function buttonCls(variant: ButtonVariant = 'primary', size: ButtonSize = 'md'): string {
  return `${SIZE_CLS[size]} ${VARIANT_CLS[variant]} rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed`;
}

/**
 * When `loading` is true the button is disabled and — if a `loadingLabel` is
 * given — shows that label instead of its children. This reproduces the
 * `disabled={saving}` + `{saving ? 'Adding…' : 'Add'}` pattern pages hand-roll
 * inline, so a caller can write `<Button loading={saving} loadingLabel="Adding…">Add</Button>`.
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  type = 'button',
  loading = false,
  loadingLabel,
  disabled,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  loadingLabel?: ReactNode;
}) {
  return (
    <button
      type={type}
      className={`${buttonCls(variant, size)} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && loadingLabel !== undefined ? loadingLabel : children}
    </button>
  );
}

/** Link styled as a button — for "New …" actions that navigate. */
export function ButtonLink({
  href,
  variant = 'primary',
  size = 'md',
  className = '',
  children,
}: {
  href: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link href={href} className={`inline-block ${buttonCls(variant, size)} ${className}`}>
      {children}
    </Link>
  );
}
