/**
 * Shared style tokens. These are the raw Tailwind class strings that used to be
 * copy-pasted across pages (or exported from layout components). Keeping them
 * here — decoupled from any one component — lets forms and inputs share the
 * exact same look without importing a layout module just for a class string.
 */

/** Standard text-input / select / textarea styling used by every form field. */
export const inputCls =
  'w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent';

/**
 * File picker. The `file:` variants restyle the browser's own button, which no
 * component layer can wrap — so the class string lives here rather than being
 * copy-pasted into whichever page happens to accept an upload.
 */
export const fileInputCls =
  'block w-full text-sm text-muted file:mr-3 file:py-2 file:px-4 file:rounded file:border-0 file:bg-accent-wash file:text-accent-text file:text-sm file:font-medium hover:file:bg-accent-wash';

/**
 * Rows for content hidden from students (issue #338).
 *
 * A lecturer keeps seeing every hidden unit and assignment -- only students
 * lose them -- so these rows are dimmed rather than removed. The `muted` tone
 * from the design spec covers chips, but a whole dimmed *row* has no component
 * of its own yet; these strings keep the palette utilities inside the
 * component layer until one exists.
 */
export const hiddenRowCls = 'bg-canvas';
export const hiddenRowTitleCls = 'text-subtle';
export const rowTitleCls = 'text-fg';
/** Dot / icon alongside a dimmed row. */
export const hiddenRowMarkCls = 'opacity-40';

/** An input showing a value the user cannot change (e.g. an immutable path). */
export const readOnlyInputCls = `${inputCls} bg-canvas text-muted`;
