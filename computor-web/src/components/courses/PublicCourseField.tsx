'use client';

/**
 * The self-registration switch for a course (issue #213).
 *
 * A checkbox rather than a `Toggle`: this sits inside the General form and
 * takes effect on Save with the rest of it, whereas `Toggle` is documented for
 * settings that apply immediately.
 *
 * The copy carries the two consequences a lecturer cannot infer from the label
 * — that the audience is every account on the instance, not just their
 * students, and that turning it off does not remove anyone who already joined.
 */
export default function PublicCourseField({
  value,
  onChange,
  disabled,
}: {
  value: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className="flex items-start gap-3 text-sm text-gray-700">
      <input
        type="checkbox"
        checked={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
      />
      <span>
        <span className="block font-medium text-gray-900">
          List this course for self-registration
        </span>
        <span className="block text-xs text-gray-600">
          Every signed-in user — not only your students — sees it in the course catalog and can
          join themselves as a student. Course content stays hidden until they join. Turning this
          off stops new registrations but keeps everyone who already joined.
        </span>
      </span>
    </label>
  );
}
