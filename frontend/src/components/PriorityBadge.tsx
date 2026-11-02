import React from 'react';
import { AlertCircle, AlertTriangle, ArrowDown, ArrowUp } from 'lucide-react';
import { TicketPriority } from '../types';

interface Props {
  priority: TicketPriority | string;
  size?: 'sm' | 'md';
}

export const PriorityBadge: React.FC<Props> = ({ priority = 'medium', size = 'md' }) => {
  const p = priority.toLowerCase();

  const getStyle = () => {
    switch (p) {
      case 'critical':
        return {
          bg: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30',
          icon: <AlertCircle className="w-3.5 h-3.5 text-red-500" />,
          label: 'Critical',
        };
      case 'high':
        return {
          bg: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/30',
          icon: <AlertTriangle className="w-3.5 h-3.5 text-orange-500" />,
          label: 'High',
        };
      case 'medium':
        return {
          bg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
          icon: <ArrowUp className="w-3.5 h-3.5 text-amber-500" />,
          label: 'Medium',
        };
      case 'low':
      default:
        return {
          bg: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/30',
          icon: <ArrowDown className="w-3.5 h-3.5 text-slate-500" />,
          label: 'Low',
        };
    }
  };

  const style = getStyle();

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium border rounded-md capitalize ${
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs'
      } ${style.bg}`}
    >
      {style.icon}
      {style.label}
    </span>
  );
};

