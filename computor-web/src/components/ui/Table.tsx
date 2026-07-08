import {
  type HTMLAttributes,
  type TableHTMLAttributes,
  type ThHTMLAttributes,
  type TdHTMLAttributes,
} from 'react';

/**
 * Table primitives that bake in the exact Tailwind class strings previously
 * copy-pasted across every admin/workspace table. Each part renders the same
 * base classes it replaces; an optional `className` is APPENDED (never
 * replaces the base), so `<Th className="text-right">` reproduces the old
 * `${thCls} text-right` string byte-for-byte. Sites whose base string differs
 * from these defaults are intentionally left as raw elements.
 */

/** Join a base class string with an optional extra, without a trailing space. */
function cx(base: string, extra?: string): string {
  return extra ? `${base} ${extra}` : base;
}

const TABLE_CLS = 'min-w-full divide-y divide-gray-200';
const THEAD_CLS = 'bg-gray-50 sticky top-0 z-10';
const TBODY_CLS = 'divide-y divide-gray-100';
const TH_CLS = 'px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider';
const TD_CLS = 'px-4 py-3';

export function Table({ className, ...rest }: TableHTMLAttributes<HTMLTableElement>) {
  return <table className={cx(TABLE_CLS, className)} {...rest} />;
}

export function Thead({ className, ...rest }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={cx(THEAD_CLS, className)} {...rest} />;
}

export function Tbody({ className, ...rest }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cx(TBODY_CLS, className)} {...rest} />;
}

/** Row wrapper. No base classes — only emits a `class` attribute when given one. */
export function Tr({ className, ...rest }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={className} {...rest} />;
}

export function Th({ className, ...rest }: ThHTMLAttributes<HTMLTableCellElement>) {
  return <th className={cx(TH_CLS, className)} {...rest} />;
}

export function Td({ className, ...rest }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cx(TD_CLS, className)} {...rest} />;
}
