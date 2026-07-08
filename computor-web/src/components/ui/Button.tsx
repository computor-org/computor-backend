'use client';

import { ButtonHTMLAttributes, ReactNode } from 'react';
import Link from 'next/link';

/**
 * Shared button. The primary/danger/secondary/ghost variants match the styles
 * that were previously copy-pasted across pages — use this instead of raw
 * class strings so the palette stays in one place.
 */
export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
export type ButtonSize = 'sm' | 'md';

const VARIANT_CLS: Record<ButtonVariant, string> = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'border border-gray-300 text-gray-700 bg-white hover:bg-gray-50',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  ghost: 'text-gray-600 hover:bg-gray-100',
};

const SIZE_CLS: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs',
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
