'use client';

/**
 * Per-course switch that routes unaddressed student messages to the AI tutor.
 *
 * A checkbox, like `PublicCourseField`: it sits inside a form and takes effect
 * on Save (or on Create) with the rest of it.
 *
 * The copy states what a lecturer cannot infer from the label: the mention is
 * visible to everyone in the thread, and staff messages and messages that
 * already address someone are never rewritten.
 */
export default function TutorAgentAutoRouteField({
  value,
  onChange,
  disabled,
}: {
  value: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className="flex items-start gap-3 text-sm text-body">
      <input
        type="checkbox"
        checked={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 rounded border-rule-strong text-accent-text focus:ring-accent-line disabled:opacity-50"
      />
      <span>
        <span className="block font-medium text-fg">
          Send student messages without an @mention to Lena
        </span>
        <span className="block text-xs text-muted">
          A student message that addresses nobody gets a visible @Lena and is answered by the AI
          tutor. Messages that mention someone, and messages from staff, are left as written. Useful
          for courses without tutors.
        </span>
      </span>
    </label>
  );
}
