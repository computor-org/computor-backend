'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import type { CourseMemberGradingsList } from 'types/generated';

const COPY = {
  de: { title: 'Verteilung des Fortschritts', students: (n: unknown) => `${n} Studierende`, count: 'Anzahl' },
  en: { title: 'Progress Distribution', students: (n: unknown) => `${n} students`, count: 'Count' },
};

interface ProgressDistributionChartProps {
  students: CourseMemberGradingsList[];
}

export default function ProgressDistributionChart({ students }: ProgressDistributionChartProps) {
  const t = COPY[useUiLanguage()];
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
    <div className="bg-surface rounded-lg border border-rule p-5">
      <h3 className="text-sm font-semibold text-fg mb-4">{t.title}</h3>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="range" tick={{ fontSize: 11 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ fontSize: 12 }}
              formatter={(value) => [t.students(value), t.count]}
            />
            <Bar dataKey="students" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
