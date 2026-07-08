/**
 * Shared style tokens. These are the raw Tailwind class strings that used to be
 * copy-pasted across pages (or exported from layout components). Keeping them
 * here — decoupled from any one component — lets forms and inputs share the
 * exact same look without importing a layout module just for a class string.
 */

/** Standard text-input / select / textarea styling used by every form field. */
export const inputCls =
  'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent';
