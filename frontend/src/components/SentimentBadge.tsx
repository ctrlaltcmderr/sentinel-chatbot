import React from 'react';
import { SentimentType } from '../types';

interface Props {
  sentiment?: SentimentType | string;
  confidence?: number;
  isHighRisk?: boolean;
  size?: 'sm' | 'md';
}

export const SentimentBadge: React.FC<Props> = ({
  sentiment = 'neutral',
  confidence,
  isHighRisk = false,
  size = 'sm',
}) => {
  const s = (sentiment || 'neutral').toLowerCase();

  const getStyle = () => {
    // If flagged as high-risk, critical red override
    if (isHighRisk || s === 'urgent') {
      return {
        pill: 'bg-red-500/10 text-red-400 border-red-500/20',
        dot: 'bg-red-500',
        label: isHighRisk ? 'Critical Risk' : 'Urgent',
      };
    }

    switch (s) {
      case 'positive':
        return {
          pill: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
          dot: 'bg-emerald-500',
          label: 'Positive',
        };
      case 'negative':
        return {
          pill: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
          dot: 'bg-amber-500',
          label: 'Negative',
        };
      case 'frustrated':
        return {
          pill: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
          dot: 'bg-amber-500',
          label: 'Frustrated',
        };
      case 'sarcastic':
        return {
          pill: 'bg-zinc-800/80 text-zinc-300 border-zinc-700/60 dark:bg-zinc-800/60 dark:text-zinc-300',
          dot: 'bg-zinc-400',
          label: 'Sarcastic',
        };
      case 'neutral':
      default:
        return {
          pill: 'bg-zinc-800/50 text-zinc-400 border-zinc-700/40 dark:bg-zinc-800/40 dark:text-zinc-400',
          dot: 'bg-zinc-500',
          label: 'Neutral',
        };
    }
  };

  const style = getStyle();

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium border rounded-md capitalize tabular-nums transition-colors ${
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'
      } ${style.pill}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${style.dot}`} />
      <span>{style.label}</span>
      {typeof confidence === 'number' && (
        <span className="text-[10px] opacity-70 font-mono ml-0.5">
          {Math.round(confidence * 100)}%
        </span>
      )}
    </span>
  );
};
