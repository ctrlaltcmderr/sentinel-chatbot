import React from 'react';
import { Smile, Meh, Frown, Flame, Zap, Sparkles, ShieldAlert } from 'lucide-react';
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
  size = 'md',
}) => {
  const s = (sentiment || 'neutral').toLowerCase();

  const getStyle = () => {
    switch (s) {
      case 'positive':
        return {
          bg: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
          icon: <Smile className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />,
          label: 'Positive',
        };
      case 'negative':
        return {
          bg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
          icon: <Frown className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />,
          label: 'Negative',
        };
      case 'frustrated':
        return {
          bg: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20',
          icon: <Flame className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />,
          label: 'Frustrated',
        };
      case 'urgent':
        return {
          bg: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
          icon: <Zap className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />,
          label: 'Urgent',
        };
      case 'sarcastic':
        return {
          bg: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20',
          icon: <Sparkles className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />,
          label: 'Sarcastic',
        };
      case 'neutral':
      default:
        return {
          bg: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20',
          icon: <Meh className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />,
          label: 'Neutral',
        };
    }
  };

  const style = getStyle();

  return (
    <div className="inline-flex items-center gap-1.5">
      <span
        className={`inline-flex items-center gap-1 font-medium border rounded-full ${
          size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs'
        } ${style.bg}`}
      >
        {style.icon}
        <span className="capitalize">{style.label}</span>
        {confidence !== undefined && (
          <span className="opacity-70 text-[10px]">({Math.round(confidence * 100)}%)</span>
        )}
      </span>

      {isHighRisk && (
        <span
          className={`inline-flex items-center gap-1 font-semibold text-rose-600 dark:text-rose-400 bg-rose-500/15 border border-rose-500/30 rounded-full animate-pulse ${
            size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs'
          }`}
        >
          <ShieldAlert className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
          HIGH RISK
        </span>
      )}
    </div>
  );
};

