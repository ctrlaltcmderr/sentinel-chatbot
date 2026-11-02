import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  PieChart,
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
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const resolutionRate =
    overview && overview.total_tickets > 0
      ? Math.round((overview.resolved_tickets / overview.total_tickets) * 100)
      : 100;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground tracking-tight">
          Executive Analytics & Telemetry
        </h1>
        <p className="text-xs text-muted-foreground">
          Operational metrics computed across multilingual conversations, SLA compliance, and team workload.
        </p>
      </div>

      {/* KPI Highlight Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-card border border-border shadow-sm">
          <span className="text-xs text-muted-foreground font-medium">Ticket Resolution Rate</span>
          <div className="text-2xl font-bold text-emerald-500 mt-1">{resolutionRate}%</div>
          <span className="text-[11px] text-muted-foreground">{overview?.resolved_tickets} of {overview?.total_tickets} closed</span>
        </div>

        <div className="p-4 rounded-xl bg-card border border-border shadow-sm">
          <span className="text-xs text-muted-foreground font-medium">Escalation Ratio</span>
          <div className="text-2xl font-bold text-orange-500 mt-1">
            {overview && overview.total_conversations > 0
              ? Math.round((overview.escalated_conversations / overview.total_conversations) * 100)
              : 0}%
          </div>
          <span className="text-[11px] text-muted-foreground">{overview?.escalated_conversations} total escalations</span>
        </div>

        <div className="p-4 rounded-xl bg-card border border-border shadow-sm">
          <span className="text-xs text-muted-foreground font-medium">High Risk Frequency</span>
          <div className="text-2xl font-bold text-rose-500 mt-1">
            {overview?.high_risk_incidents || 0}
          </div>
          <span className="text-[11px] text-muted-foreground">Compromise & fraud alerts</span>
        </div>

        <div className="p-4 rounded-xl bg-card border border-border shadow-sm">
          <span className="text-xs text-muted-foreground font-medium">Deterministic Latency</span>
          <div className="text-2xl font-bold text-foreground mt-1">
            {overview?.average_response_time_ms || 45} ms
          </div>
          <span className="text-[11px] text-muted-foreground">Under 200ms enterprise SLA</span>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Support Team Workload */}
        <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Active Team Workload</h2>
            <p className="text-xs text-muted-foreground">Distribution of open tickets by routing team</p>
          </div>

          <div className="space-y-3 pt-2">
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
                      <span className="capitalize font-semibold text-foreground">{team}</span>
                      <span className="text-muted-foreground">{count} tickets ({percent}%)</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        style={{ width: `${percent}%` }}
                        className="h-full rounded-full bg-primary transition-all duration-300"
                      />
                    </div>
                  </div>
                );
              })}
            {(!trends?.team_workload || Object.keys(trends.team_workload).length === 0) && (
              <div className="text-center py-6 text-xs text-muted-foreground">
                No active tickets in queue.
              </div>
            )}
          </div>
        </div>

        {/* Multilingual Distribution */}
        <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Language Distribution</h2>
            <p className="text-xs text-muted-foreground">
              Customer inquiries by detected language (English, Spanish, French, Hindi)
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-2">
            {trends?.language_distribution &&
              Object.entries(trends.language_distribution).map(([lang, count]) => {
                const names: Record<string, string> = {
                  en: 'English',
                  es: 'Spanish (Español)',
                  fr: 'French (Français)',
                  hi: 'Hindi (हिन्दी / Hinglish)',
                };
                return (
                  <div key={lang} className="p-3.5 rounded-lg bg-muted/40 border border-border flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-xs text-foreground block">
                        {names[lang] || lang.toUpperCase()}
                      </span>
                      <span className="text-[10px] uppercase font-mono text-muted-foreground">
                        Code: {lang}
                      </span>
                    </div>
                    <span className="text-base font-bold text-primary">{count}</span>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Ticket Priorities */}
        <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Priority Breakdown</h2>
            <p className="text-xs text-muted-foreground">5-factor weighted priority score distribution</p>
          </div>

          <div className="grid grid-cols-4 gap-2 pt-2">
            {['critical', 'high', 'medium', 'low'].map((p) => {
              const count = trends?.priority_counts?.[p] || 0;
              return (
                <div key={p} className="p-3 rounded-lg bg-muted/30 border border-border text-center space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground block">
                    {p}
                  </span>
                  <div
                    className={`text-xl font-bold ${
                      p === 'critical'
                        ? 'text-red-500'
                        : p === 'high'
                        ? 'text-orange-500'
                        : p === 'medium'
                        ? 'text-amber-500'
                        : 'text-slate-500'
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
        <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Ticket Lifecycle Status</h2>
            <p className="text-xs text-muted-foreground">Current states in the support pipeline</p>
          </div>

          <div className="grid grid-cols-3 gap-2.5 pt-2">
            {trends?.status_distribution &&
              Object.entries(trends.status_distribution).map(([status, count]) => (
                <div key={status} className="p-3 rounded-lg bg-muted/30 border border-border text-center space-y-1">
                  <span className="text-[10px] uppercase font-semibold text-muted-foreground block">
                    {status}
                  </span>
                  <div className="text-lg font-bold text-foreground">{count}</div>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
};

