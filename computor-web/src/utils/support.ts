import type { TicketPriority, TicketStatus, TicketUserRef } from '@/src/clients/SupportClient';
import type { Tone } from '@/src/components/ui/tones';

export const STATUS_LABEL: Record<TicketStatus, string> = {
  open: 'Open',
  in_progress: 'In progress',
  waiting: 'Waiting',
  done: 'Done',
};

export const STATUS_TONE: Record<TicketStatus, Tone> = {
  open: 'info',
  in_progress: 'warning',
  waiting: 'muted',
  done: 'success',
};

export const PRIORITY_LABEL: Record<TicketPriority, string> = {
  low: 'Low',
  normal: 'Normal',
  high: 'High',
};

export function userLabel(u?: TicketUserRef | null): string {
  if (!u) return '';
  const name = [u.given_name, u.family_name].filter(Boolean).join(' ');
  return name || u.email || u.id;
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString();
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
