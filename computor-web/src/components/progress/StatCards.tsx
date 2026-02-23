'use client';

import type { CourseMemberGradingsList } from 'types/generated';

interface StatCardsProps {
  students: CourseMemberGradingsList[];
}

function daysSince(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  const diff = Date.now() - new Date(dateStr).getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24));
}

export default function StatCards({ students }: StatCardsProps) {
  const total = students.length;
  const avgProgress = total > 0
    ? Math.round(students.reduce((sum, s) => sum + s.overall_progress_percentage, 0) / total)
    : 0;
  const completed = students.filter(s => s.overall_progress_percentage >= 100).length;
  const atRisk = students.filter(s => s.overall_progress_percentage < 25).length;
  const inactive = students.filter(s => {
    const days = daysSince(s.latest_submission_at);
    return days === null || days > 14;
  }).length;

  const cards = [
    { label: 'Total Students', value: total, color: 'blue' },
    { label: 'Average Progress', value: `${avgProgress}%`, color: 'indigo' },
    { label: 'Completed', value: completed, color: 'green' },
    { label: 'At Risk', value: atRisk, color: 'red' },
    { label: 'Inactive (14d+)', value: inactive, color: 'yellow' },
  ];

  const colorMap: Record<string, { bg: string; text: string; ring: string }> = {
    blue: { bg: 'bg-blue-50', text: 'text-blue-700', ring: 'ring-blue-200' },
    indigo: { bg: 'bg-indigo-50', text: 'text-indigo-700', ring: 'ring-indigo-200' },
    green: { bg: 'bg-green-50', text: 'text-green-700', ring: 'ring-green-200' },
    red: { bg: 'bg-red-50', text: 'text-red-700', ring: 'ring-red-200' },
    yellow: { bg: 'bg-amber-50', text: 'text-amber-700', ring: 'ring-amber-200' },
  };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      {cards.map((card) => {
        const c = colorMap[card.color];
        return (
          <div key={card.label} className={`${c.bg} rounded-lg p-4 ring-1 ${c.ring}`}>
            <p className="text-xs font-medium text-gray-500">{card.label}</p>
            <p className={`text-2xl font-bold mt-1 ${c.text}`}>{card.value}</p>
          </div>
        );
      })}
    </div>
  );
}
