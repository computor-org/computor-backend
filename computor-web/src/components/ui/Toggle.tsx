'use client';

/**
 * On/off switch for a setting that takes effect immediately.
 *
 * Use it where the control IS the state — "available to users", "provisioning
 * enabled" — rather than a button whose label is the action ("Disable"). A
 * button in that position makes the reader work out the current state from the
 * inverse of what the button offers, and it reads wrong in a table column
 * headed by the state's name.
 *
 * A real <button role="switch">, so keyboard and screen readers get the
 * platform behaviour; `busy` keeps the switch showing the old state (rather
 * than flickering to the new one) until the server confirms.
 */
export default function Toggle({
  checked,
  onChange,
  label,
  disabled = false,
  busy = false,
  title,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  /** Accessible name — the switch itself has no visible text. */
  label: string;
  disabled?: boolean;
  busy?: boolean;
  title?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      title={title}
      disabled={disabled || busy}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-line focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${
        checked ? 'bg-accent' : 'bg-gray-300'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-surface shadow transition-transform ${
          checked ? 'translate-x-4.5' : 'translate-x-0.5'
        }`}
      />
    </button>
  );
}
