import React from 'react';
import { AlertCircle, AlertTriangle, ArrowDown, ArrowUp } from 'lucide-react';
import { TicketPriority } from '../types';

interface Props {
  priority: TicketPriority | string;
  size?: 'sm' | 'md';
}

export const PriorityBadge: React.FC<Props> = ({ priority = 'medium', size = 'sm' }) => {
  const p = priority.toLowerCase();

  const getStyle = () => {
    switch (p) {
      case 'critical':
        return {
          pill: 'bg-red-500/10 text-red-400 border-red-500/20',
          dot: 'bg-red-500',
          icon: <AlertCircle className="w-3 h-3 text-red-400" />,
          label: 'Critical',
        };
      case 'high':
        return {
          pill: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
          dot: 'bg-amber-500',
          icon: <AlertTriangle className="w-3 h-3 text-amber-400" />,
          label: 'High',
        };
      case 'medium':
        return {
          pill: 'bg-zinc-800/80 text-zinc-300 border-zinc-700/60 dark:bg-zinc-800/60 dark:text-zinc-300',
          dot: 'bg-zinc-400',
          icon: <ArrowUp className="w-3 h-3 text-zinc-400" />,
          label: 'Medium',
        };
      case 'low':
      default:
        return {
          pill: 'bg-zinc-800/40 text-zinc-400 border-zinc-700/40 dark:bg-zinc-800/30 dark:text-zinc-500',
          dot: 'bg-zinc-600',
          icon: <ArrowDown className="w-3 h-3 text-zinc-500" />,
          label: 'Low',
        };
    }
  };

  const style = getStyle();

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium border rounded-md tabular-nums transition-colors ${
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'
      } ${style.pill}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      <span>{style.label}</span>
    </span>
  );
};
