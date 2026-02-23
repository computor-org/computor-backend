'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { CourseMemberGradingsList } from 'types/generated';

interface ProgressDistributionChartProps {
  students: CourseMemberGradingsList[];
}

export default function ProgressDistributionChart({ students }: ProgressDistributionChartProps) {
  const buckets = Array(10).fill(0);
  students.forEach(s => {
    const idx = Math.min(Math.floor(s.overall_progress_percentage / 10), 9);
    buckets[idx]++;
  });

  const data = buckets.map((count, i) => ({
    range: `${i * 10}-${(i + 1) * 10}%`,
    students: count,
  }));

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Progress Distribution</h3>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="range" tick={{ fontSize: 11 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ fontSize: 12 }}
              formatter={(value) => [`${value} students`, 'Count']}
            />
            <Bar dataKey="students" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
