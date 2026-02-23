'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { CourseMemberGradingsList, ContentTypeGradingStats } from 'types/generated';

interface ContentTypeChartProps {
  students: CourseMemberGradingsList[];
}

export default function ContentTypeChart({ students }: ContentTypeChartProps) {
  if (students.length === 0) return null;

  // Aggregate content type stats across all students
  const typeMap = new Map<string, { title: string; color: string; totalProgress: number; count: number }>();

  students.forEach(s => {
    (s.by_content_type || []).forEach((ct: ContentTypeGradingStats) => {
      const key = ct.course_content_type_slug;
      const existing = typeMap.get(key);
      if (existing) {
        existing.totalProgress += ct.progress_percentage;
        existing.count++;
      } else {
        typeMap.set(key, {
          title: ct.course_content_type_title || ct.course_content_type_slug,
          color: ct.course_content_type_color || '#6366f1',
          totalProgress: ct.progress_percentage,
          count: 1,
        });
      }
    });
  });

  const data = Array.from(typeMap.entries()).map(([slug, info]) => ({
    name: info.title,
    progress: Math.round(info.totalProgress / info.count),
    color: info.color,
    slug,
  }));

  if (data.length === 0) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Avg Progress by Content Type</h3>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
            <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ fontSize: 12 }}
              formatter={(value) => [`${value}%`, 'Avg Progress']}
            />
            <Bar dataKey="progress" radius={[0, 4, 4, 0]}>
              {data.map((entry) => (
                <Cell key={entry.slug} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
