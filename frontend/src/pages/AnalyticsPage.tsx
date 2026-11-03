import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  Globe,
  Clock,
  ShieldAlert,
  Users,
  CheckCircle2,
  Calendar,
} from 'lucide-react';
import { api } from '../api/client';
import { AnalyticsOverview, AnalyticsTrends } from '../types';

export const AnalyticsPage: React.FC = () => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [trends, setTrends] = useState<AnalyticsTrends | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const [ov, tr] = await Promise.all([
          api.getAnalyticsOverview(),
          api.getAnalyticsTrends(),
        ]);
        setOverview(ov);
        setTrends(tr);
      } catch (err) {
        console.error('Failed to load analytics:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (loading && !overview) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="w-6 h-6 border-2 border-zinc-500 border-t-zinc-200 rounded-full animate-spin" />
      </div>
    );
  }

  const resolutionRate =
    overview && overview.total_tickets > 0
      ? Math.round((overview.resolved_tickets / overview.total_tickets) * 100)
      : 100;

  const escalationRatio =
    overview && overview.total_conversations > 0
      ? Math.round((overview.escalated_conversations / overview.total_conversations) * 100)
      : 0;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="border-b border-border pb-4">
        <h1 className="text-lg font-semibold text-zinc-100 tracking-tight">
          Executive Telemetry & BI Operations
        </h1>
        <p className="text-xs text-zinc-400 mt-0.5">
          Operational metrics computed across multilingual conversations, SLA compliance, and team workload.
        </p>
      </div>

      {/* KPI Highlight Strip */}
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <div className="grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-border">
          <div className="p-4 lg:p-5 flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
              Resolution Efficiency
            </span>
            <div className="mt-2">
              <div className="text-2xl font-semibold font-mono tracking-tight text-emerald-400 tabular-nums">
                {resolutionRate}%
              </div>
              <span className="text-[11px] text-zinc-500 mt-1 block">
                {overview?.resolved_tickets} of {overview?.total_tickets} closed
              </span>
            </div>
          </div>

          <div className="p-4 lg:p-5 flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
              Escalation Ratio
            </span>
            <div className="mt-2">
              <div className="text-2xl font-semibold font-mono tracking-tight text-amber-400 tabular-nums">
                {escalationRatio}%
              </div>
              <span className="text-[11px] text-zinc-500 mt-1 block">
                {overview?.escalated_conversations} total escalations
              </span>
            </div>
          </div>

          <div className="p-4 lg:p-5 flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
              High-Risk Incidents
            </span>
            <div className="mt-2">
              <div className={`text-2xl font-semibold font-mono tracking-tight tabular-nums ${
                (overview?.high_risk_incidents || 0) > 0 ? 'text-red-400' : 'text-zinc-100'
              }`}>
                {overview?.high_risk_incidents || 0}
              </div>
              <span className="text-[11px] text-zinc-500 mt-1 block">
                Account breach & fraud alerts
              </span>
            </div>
          </div>

          <div className="p-4 lg:p-5 flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
              Mean Latency
            </span>
            <div className="mt-2">
              <div className="text-2xl font-semibold font-mono tracking-tight text-zinc-100 tabular-nums">
                {overview?.average_response_time_ms || 42} <span className="text-xs font-normal text-zinc-500">ms</span>
              </div>
              <span className="text-[11px] text-zinc-500 mt-1 block">
                P99 response SLA target: 200ms
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Support Team Workload */}
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Active Team Workload Dispatch
            </h2>
            <p className="text-[11px] text-zinc-500 mt-0.5">Distribution of open tickets by specialized routing team</p>
          </div>

          <div className="space-y-3 pt-1">
            {trends?.team_workload &&
              Object.entries(trends.team_workload).map(([team, count]) => {
                const total = Math.max(
                  Object.values(trends.team_workload).reduce((a, b) => a + b, 0),
                  1
                );
                const percent = Math.round((count / total) * 100);

                return (
                  <div key={team} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="capitalize font-medium text-zinc-200">{team} Team</span>
                      <span className="font-mono text-[11px] text-zinc-400">
                        {count} tickets <span className="text-zinc-600">({percent}%)</span>
                      </span>
                    </div>
                    <div className="w-full h-1.5 rounded-sm bg-zinc-800 overflow-hidden">
                      <div
                        style={{ width: `${percent}%` }}
                        className="h-full rounded-sm bg-zinc-400 transition-all duration-300"
                      />
                    </div>
                  </div>
                );
              })}
            {(!trends?.team_workload || Object.keys(trends.team_workload).length === 0) && (
              <div className="text-center py-6 text-xs text-zinc-500 font-mono">
                No active tickets in queue.
              </div>
            )}
          </div>
        </div>

        {/* Multilingual Distribution */}
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Language Demographics
            </h2>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              Customer inquiries categorized by real-time language detection
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            {trends?.language_distribution &&
              Object.entries(trends.language_distribution).map(([lang, count]) => {
                const names: Record<string, string> = {
                  en: 'English',
                  es: 'Spanish',
                  fr: 'French',
                  hi: 'Hindi / Hinglish',
                };
                return (
                  <div key={lang} className="p-3 rounded-md bg-zinc-900/60 border border-border flex items-center justify-between">
                    <div>
                      <span className="font-medium text-xs text-zinc-200 block">
                        {names[lang] || lang.toUpperCase()}
                      </span>
                      <span className="text-[10px] uppercase font-mono text-zinc-500">
                        ISO: {lang}
                      </span>
                    </div>
                    <span className="text-base font-semibold font-mono text-zinc-100 tabular-nums">{count}</span>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Ticket Priorities */}
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Priority Stratification
            </h2>
            <p className="text-[11px] text-zinc-500 mt-0.5">5-factor weighted priority score distribution</p>
          </div>

          <div className="grid grid-cols-4 gap-2.5 pt-1">
            {['critical', 'high', 'medium', 'low'].map((p) => {
              const count = trends?.priority_counts?.[p] || 0;
              return (
                <div key={p} className="p-3 rounded-md bg-zinc-900/50 border border-border text-center space-y-1">
                  <span className="text-[10px] uppercase font-mono font-medium text-zinc-500 block">
                    {p}
                  </span>
                  <div
                    className={`text-xl font-semibold font-mono tabular-nums ${
                      p === 'critical'
                        ? 'text-red-400'
                        : p === 'high'
                        ? 'text-amber-400'
                        : p === 'medium'
                        ? 'text-zinc-300'
                        : 'text-zinc-500'
                    }`}
                  >
                    {count}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Ticket Status Lifecycle */}
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Support Lifecycle Pipeline
            </h2>
            <p className="text-[11px] text-zinc-500 mt-0.5">Current operational state distribution across all tickets</p>
          </div>

          <div className="grid grid-cols-3 gap-2.5 pt-1">
            {trends?.status_distribution &&
              Object.entries(trends.status_distribution).map(([status, count]) => (
                <div key={status} className="p-3 rounded-md bg-zinc-900/50 border border-border text-center space-y-1">
                  <span className="text-[10px] uppercase font-medium text-zinc-500 block truncate">
                    {status}
                  </span>
                  <div className="text-lg font-semibold font-mono text-zinc-200 tabular-nums">{count}</div>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
};
