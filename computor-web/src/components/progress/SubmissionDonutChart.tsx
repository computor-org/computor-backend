'use client';

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import type { ContentTypeGradingStats } from 'types/generated';

interface SubmissionDonutChartProps {
  byContentType: ContentTypeGradingStats[];
  totalMax: number;
  totalSubmitted: number;
}

export default function SubmissionDonutChart({ byContentType, totalMax, totalSubmitted }: SubmissionDonutChartProps) {
  const remaining = Math.max(0, totalMax - totalSubmitted);

  const data = [
    ...byContentType.map(ct => ({
      name: ct.course_content_type_title || ct.course_content_type_slug,
      value: ct.submitted_assignments,
      color: ct.course_content_type_color || '#6366f1',
      max: ct.max_assignments,
    })),
    ...(remaining > 0
      ? [{ name: 'Remaining', value: remaining, color: '#e5e7eb', max: remaining }]
      : []),
  ].filter(d => d.value > 0);

  if (data.length === 0) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Submissions by Type</h3>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius="55%"
              outerRadius="80%"
              paddingAngle={2}
              dataKey="value"
            >
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ fontSize: 12 }}
              formatter={(value, name) => {
                const pct = totalMax > 0 ? Math.round((Number(value) / totalMax) * 100) : 0;
                return [`${value} (${pct}%)`, name];
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      {/* Legend */}
      <div className="mt-3 space-y-1.5">
        {byContentType.map(ct => {
          const pct = ct.max_assignments > 0
            ? Math.round((ct.submitted_assignments / ct.max_assignments) * 100)
            : 0;
          return (
            <div key={ct.course_content_type_id} className="flex items-center gap-2 text-xs">
              <span
                className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: ct.course_content_type_color || '#6366f1' }}
              />
              <span className="text-gray-700 truncate">
                {ct.course_content_type_title || ct.course_content_type_slug}
              </span>
              <span className="text-gray-400 ml-auto flex-shrink-0">
                {ct.submitted_assignments}/{ct.max_assignments} ({pct}%)
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
