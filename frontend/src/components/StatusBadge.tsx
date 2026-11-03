import React from 'react';
import { TicketStatus } from '../types';

interface Props {
  status: TicketStatus | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<Props> = ({ status = 'Open', size = 'sm' }) => {
  const s = status.toLowerCase();

  const getStyle = () => {
    switch (s) {
      case 'open':
        return {
          pill: 'bg-zinc-800/70 text-zinc-300 border-zinc-700/60 dark:bg-zinc-800/60 dark:text-zinc-200',
          dot: 'bg-zinc-400',
        };
      case 'in progress':
        return {
          pill: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
          dot: 'bg-indigo-400',
        };
      case 'pending':
        return {
          pill: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
          dot: 'bg-amber-400',
        };
      case 'escalated':
        return {
          pill: 'bg-red-500/10 text-red-400 border-red-500/20 font-medium',
          dot: 'bg-red-500 animate-pulse',
        };
      case 'resolved':
        return {
          pill: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
          dot: 'bg-emerald-500',
        };
      case 'closed':
      default:
        return {
          pill: 'bg-zinc-800/40 text-zinc-500 border-zinc-800/60',
          dot: 'bg-zinc-600',
        };
    }
  };

  const style = getStyle();

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium border rounded-md capitalize ${
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'
      } ${style.pill}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${style.dot}`} />
      <span className="truncate">{status}</span>
    </span>
  );
};
