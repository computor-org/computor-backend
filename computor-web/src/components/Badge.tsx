'use client';

import { ReactNode } from 'react';

/**
 * Shared status/role chip. One color per semantic meaning, one shape per
 * concept — replaces the ad-hoc badge spans whose colors drifted per page
 * (green-700 vs green-800, blue vs indigo role tags, rounded vs rounded-full).
 */
export type BadgeColor =
  | 'green' // success / active
  | 'red' // danger / error / archived-with-alarm
  | 'yellow' // warning / pending
  | 'blue' // info / role tag
  | 'purple' // special roles
  | 'gray'; // neutral / archived

const COLOR_CLS: Record<BadgeColor, string> = {
  green: 'bg-green-100 text-green-800',
  red: 'bg-red-100 text-red-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  blue: 'bg-blue-100 text-blue-800',
  purple: 'bg-purple-100 text-purple-800',
  gray: 'bg-gray-100 text-gray-700',
};

export default function Badge({
  color = 'gray',
  pill = false,
  className = '',
  children,
}: {
  color?: BadgeColor;
  /** Pills for live statuses (running/active), squares for classifications. */
  pill?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-medium ${
        pill ? 'rounded-full' : 'rounded'
      } ${COLOR_CLS[color]} ${className}`}
    >
      {children}
    </span>
  );
}
