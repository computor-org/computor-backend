/**
 * Shared style tokens. These are the raw Tailwind class strings that used to be
 * copy-pasted across pages (or exported from layout components). Keeping them
 * here — decoupled from any one component — lets forms and inputs share the
 * exact same look without importing a layout module just for a class string.
 */

/** Standard text-input / select / textarea styling used by every form field. */
export const inputCls =
  'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent';

/**
 * File picker. The `file:` variants restyle the browser's own button, which no
 * component layer can wrap — so the class string lives here rather than being
 * copy-pasted into whichever page happens to accept an upload.
 */
export const fileInputCls =
  'block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-50 file:text-blue-700 file:text-sm file:font-medium hover:file:bg-blue-100';

/**
 * Rows for content hidden from students (issue #338).
 *
 * A lecturer keeps seeing every hidden unit and assignment -- only students
 * lose them -- so these rows are dimmed rather than removed. The `muted` tone
 * from the design spec covers chips, but a whole dimmed *row* has no component
 * of its own yet; these strings keep the palette utilities inside the
 * component layer until one exists.
 */
export const hiddenRowCls = 'bg-gray-50';
export const hiddenRowTitleCls = 'text-gray-400';
export const rowTitleCls = 'text-gray-900';
/** Dot / icon alongside a dimmed row. */
export const hiddenRowMarkCls = 'opacity-40';

/** An input showing a value the user cannot change (e.g. an immutable path). */
export const readOnlyInputCls = `${inputCls} bg-gray-50 text-gray-500`;
