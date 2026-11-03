import React, { useEffect, useState } from 'react';
import {
  ArrowRight,
  TrendingUp,
  ShieldAlert,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowUpRight,
  Activity,
  Layers,
} from 'lucide-react';
import { api } from '../api/client';
import { AnalyticsOverview, AnalyticsTrends, Conversation, Ticket as TicketType } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import { StatusBadge } from '../components/StatusBadge';

interface Props {
  onNavigate: (tab: string, sessionId?: string) => void;
}

export const DashboardPage: React.FC<Props> = ({ onNavigate }) => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [trends, setTrends] = useState<AnalyticsTrends | null>(null);
  const [recentConversations, setRecentConversations] = useState<Conversation[]>([]);
  const [recentTickets, setRecentTickets] = useState<TicketType[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [ov, tr, convs, tkts] = await Promise.all([
        api.getAnalyticsOverview(),
        api.getAnalyticsTrends(),
        api.getConversations(),
        api.getTickets(),
      ]);
      setOverview(ov);
      setTrends(tr);
      setRecentConversations(convs.slice(0, 6));
      setRecentTickets(tkts.slice(0, 6));
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading && !overview) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-zinc-500 border-t-zinc-200 rounded-full animate-spin" />
          <span className="text-xs text-zinc-500 font-mono">Loading operations telemetry...</span>
        </div>
      </div>
    );
  }

  const totalInquiries = overview?.total_conversations || 0;
  const activeConversations = overview?.active_conversations || 0;
  const totalTickets = overview?.total_tickets || 0;
  const openTickets = overview?.open_tickets || 0;
  const escalatedCount = overview?.escalated_conversations || 0;
  const highRiskCount = overview?.high_risk_incidents || 0;
  const resolvedCount = overview?.resolved_tickets || 0;
  const latencyMs = overview?.average_response_time_ms || 42;

  const escalationRate = totalInquiries > 0 ? Math.round((escalatedCount / totalInquiries) * 100) : 0;
  const resolutionRate = totalTickets > 0 ? Math.round((resolvedCount / totalTickets) * 100) : 100;

  // Sentiment distribution calculations
  const sentimentCounts = trends?.sentiment_counts || {};
  const totalSentiments = Math.max(
    Object.values(sentimentCounts).reduce((a, b) => a + b, 0),
    1
  );

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100 tracking-tight">Operations Dashboard</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Real-time telemetry across multi-modal inquiries, calendar-aware SLAs, and escalation queues.
          </p>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            onClick={() => onNavigate('chat')}
            className="px-3 py-1.5 rounded-md bg-zinc-100 text-zinc-950 hover:bg-white text-xs font-medium transition-colors shadow-sm flex items-center gap-1.5"
          >
            New Session
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* KPI Section: Unified Metric Strip with Understated Dividers */}
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 divide-y md:divide-y-0 md:divide-x divide-border">
          {/* Total Inquiries */}
          <div className="p-4 lg:p-5 flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">Total Inquiries</span>
            <div className="mt-2">
              <div className="text-2xl font-semibold font-mono tracking-tight text-zinc-100 tabular-nums">
                {totalInquiries}
              </div>
              <div className="text-[11px] text-zinc-500 mt-1 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span>{activeConversations} active</span>
              </div>
            </div>
          </div>

          {/* Support Tickets */}
          <div className="p-4 lg:p-5 flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">Support Tickets</span>
            <div className="mt-2">
              <div className="text-2xl font-semibold font-mono tracking-tight text-zinc-100 tabular-nums">
                {totalTickets}
              </div>
              <div className="text-[11px] text-zinc-500 mt-1">
                <span>{openTickets} open in queue</span>
              </div>
            </div>
          </div>

          {/* Escalated Cases */}
          <div className="p-4 lg:p-5 flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">Escalated Cases</span>
            <div className="mt-2">
              <div className="text-2xl font-semibold font-mono tracking-tight text-zinc-100 tabular-nums">
                {escalatedCount}
              </div>
              <div className="text-[11px] text-zinc-500 mt-1">
                <span>{escalationRate}% escalation rate</span>
              </div>
            </div>
          </div>

          {/* High-Risk Incidents */}
          <div className="p-4 lg:p-5 flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">High-Risk Incidents</span>
            <div className="mt-2">
              <div
                className={`text-2xl font-semibold font-mono tracking-tight tabular-nums ${
                  highRiskCount > 0 ? 'text-red-400' : 'text-zinc-100'
                }`}
              >
                {highRiskCount}
              </div>
              <div className="text-[11px] mt-1 flex items-center gap-1.5">
                {highRiskCount > 0 ? (
                  <span className="text-red-400 font-medium">Critical Review Required</span>
                ) : (
                  <span className="text-zinc-500">Zero active alerts</span>
                )}
              </div>
            </div>
          </div>

          {/* Resolved Tickets */}
          <div className="p-4 lg:p-5 flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">Resolved Tickets</span>
            <div className="mt-2">
              <div className="text-2xl font-semibold font-mono tracking-tight text-zinc-100 tabular-nums">
                {resolvedCount}
              </div>
              <div className="text-[11px] text-zinc-500 mt-1">
                <span>{resolutionRate}% resolved</span>
              </div>
            </div>
          </div>

          {/* Average Latency */}
          <div className="p-4 lg:p-5 flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">Mean Latency</span>
            <div className="mt-2">
              <div className="text-2xl font-semibold font-mono tracking-tight text-zinc-100 tabular-nums">
                {latencyMs} <span className="text-xs font-normal text-zinc-500">ms</span>
              </div>
              <div className="text-[11px] text-zinc-500 mt-1">
                <span>Deterministic SLI</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Analytics Telemetry Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 7-Day Inbound Activity Timeline */}
        <div className="lg:col-span-2 rounded-lg border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
                Conversation Activity Timeline
              </h2>
              <p className="text-[11px] text-zinc-500 mt-0.5">
                Inbound customer messages vs escalated cases (rolling 7-day window)
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs font-mono">
              <div className="flex items-center gap-1.5 text-zinc-400">
                <span className="w-2 h-2 rounded-sm bg-zinc-600" />
                <span className="text-[11px]">Total</span>
              </div>
              <div className="flex items-center gap-1.5 text-zinc-400">
                <span className="w-2 h-2 rounded-sm bg-red-500/80" />
                <span className="text-[11px]">Escalated</span>
              </div>
            </div>
          </div>

          {/* Chart with Subtle Grid Lines */}
          <div className="pt-4">
            <div className="h-48 flex items-end justify-between gap-3 border-b border-border/80 pb-2 relative">
              {/* Subtle Horizontal Grid lines */}
              <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-20">
                <div className="border-b border-zinc-600 w-full" />
                <div className="border-b border-zinc-600 w-full" />
                <div className="border-b border-zinc-600 w-full" />
              </div>

              {trends?.activity_timeline && trends.activity_timeline.length > 0 ? (
                trends.activity_timeline.map((item, idx) => {
                  const maxVal = Math.max(
                    ...trends.activity_timeline.map((t) => t.conversations),
                    5
                  );
                  const convHeight = Math.max((item.conversations / maxVal) * 100, 6);
                  const escHeight = Math.max((item.escalations / maxVal) * 100, item.escalations > 0 ? 8 : 0);

                  return (
                    <div key={idx} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group z-10">
                      <div className="w-full flex items-end justify-center gap-1 h-full">
                        {/* Total Conversations Bar */}
                        <div
                          style={{ height: `${convHeight}%` }}
                          className="w-1/2 max-w-[20px] bg-zinc-700 group-hover:bg-zinc-500 rounded-t-sm transition-colors relative flex justify-center"
                        >
                          <span className="opacity-0 group-hover:opacity-100 absolute -top-5 text-[10px] font-mono font-medium text-zinc-200 transition-opacity bg-zinc-900 px-1 py-0.5 rounded border border-zinc-800">
                            {item.conversations}
                          </span>
                        </div>
                        {/* Escalations Bar */}
                        <div
                          style={{ height: `${escHeight}%` }}
                          className="w-1/2 max-w-[20px] bg-red-500/70 group-hover:bg-red-500 rounded-t-sm transition-colors relative flex justify-center"
                        >
                          {item.escalations > 0 && (
                            <span className="opacity-0 group-hover:opacity-100 absolute -top-5 text-[10px] font-mono font-medium text-red-400 transition-opacity bg-zinc-900 px-1 py-0.5 rounded border border-zinc-800">
                              {item.escalations}
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="text-[10px] font-mono text-zinc-500">
                        {item.date.slice(5)}
                      </span>
                    </div>
                  );
                })
              ) : (
                <div className="w-full h-full flex items-center justify-center text-xs text-zinc-500">
                  No activity telemetry recorded.
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] text-zinc-500 pt-1">
            <span>Synchronized continuously from live interaction events</span>
            <button
              onClick={() => onNavigate('analytics')}
              className="text-zinc-300 hover:text-white font-medium flex items-center gap-1 transition-colors"
            >
              Open Telemetry View <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Sentiment Breakdown */}
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Sentiment Distribution
            </h2>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              Multi-class emotional analysis across customer utterances
            </p>
          </div>

          {/* GitHub-style Horizontal Proportion Stack */}
          <div className="w-full h-2 rounded-sm bg-zinc-800 overflow-hidden flex">
            {Object.entries(sentimentCounts).map(([sentiment, count]) => {
              const widthPct = (count / totalSentiments) * 100;
              if (widthPct === 0) return null;
              const color =
                sentiment === 'positive'
                  ? 'bg-emerald-500'
                  : sentiment === 'urgent'
                  ? 'bg-red-500'
                  : sentiment === 'frustrated' || sentiment === 'negative'
                  ? 'bg-amber-500'
                  : 'bg-zinc-500';
              return (
                <div
                  key={sentiment}
                  style={{ width: `${widthPct}%` }}
                  className={`h-full ${color}`}
                  title={`${sentiment}: ${count} (${Math.round(widthPct)}%)`}
                />
              );
            })}
          </div>

          {/* Category Listing */}
          <div className="space-y-2.5 pt-1">
            {Object.entries(sentimentCounts).map(([sentiment, count]) => {
              const pct = Math.round((count / totalSentiments) * 100);
              return (
                <div key={sentiment} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <SentimentBadge sentiment={sentiment} size="sm" />
                  </div>
                  <div className="flex items-center gap-2 font-mono text-[11px] text-zinc-400">
                    <span className="tabular-nums">{count}</span>
                    <span className="text-zinc-600">|</span>
                    <span className="text-zinc-500 w-8 text-right tabular-nums">{pct}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Operational Grids: Live Conversations & Support Tickets */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Conversations */}
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center justify-between">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                Recent Customer Inquiries
              </h2>
              <span className="text-[11px] text-zinc-500">Live conversations and risk evaluation</span>
            </div>
            <button
              onClick={() => onNavigate('chat')}
              className="text-xs font-medium text-zinc-400 hover:text-zinc-100 flex items-center gap-1 transition-colors"
            >
              Open Live Chat <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-border/60">
            {recentConversations.length > 0 ? (
              recentConversations.map((c) => (
                <div
                  key={c.id}
                  onClick={() => onNavigate('chat', c.id)}
                  className="px-5 py-3 flex items-center justify-between gap-3 hover:bg-zinc-900/50 cursor-pointer transition-colors"
                >
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-zinc-200 truncate">{c.title}</span>
                      {c.is_high_risk && (
                        <span className="text-[10px] font-mono font-medium text-red-400 bg-red-500/10 border border-red-500/20 px-1 rounded">
                          RISK
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-zinc-500">
                      <span>{c.customer_name || c.customer_id}</span>
                      <span>•</span>
                      <span className="font-mono">
                        {new Date(c.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                  <div className="shrink-0">
                    <SentimentBadge
                      sentiment={c.last_sentiment}
                      confidence={c.last_confidence}
                      isHighRisk={c.is_high_risk}
                      size="sm"
                    />
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-zinc-500">No recent conversations recorded.</div>
            )}
          </div>
        </div>

        {/* Recent Tickets */}
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center justify-between">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                Support Tickets Queue
              </h2>
              <span className="text-[11px] text-zinc-500">SLA deadlines and team routing</span>
            </div>
            <button
              onClick={() => onNavigate('tickets')}
              className="text-xs font-medium text-zinc-400 hover:text-zinc-100 flex items-center gap-1 transition-colors"
            >
              All Tickets <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-border/60">
            {recentTickets.length > 0 ? (
              recentTickets.map((t) => (
                <div
                  key={t.id}
                  onClick={() => onNavigate('tickets')}
                  className="px-5 py-3 flex items-center justify-between gap-3 hover:bg-zinc-900/50 cursor-pointer transition-colors"
                >
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-mono text-zinc-400">#{t.id.slice(0, 8)}</span>
                      <span className="text-xs text-zinc-200 truncate">{t.issue_description}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-zinc-500">
                      <span className="capitalize">{t.assigned_team} Team</span>
                      <span>•</span>
                      {t.sla_breached ? (
                        <span className="text-red-400 font-mono text-[10px] font-medium">SLA BREACHED</span>
                      ) : (
                        <span>Priority: <span className="capitalize text-zinc-400">{t.priority}</span></span>
                      )}
                    </div>
                  </div>
                  <div className="shrink-0 flex items-center gap-2">
                    <PriorityBadge priority={t.priority} size="sm" />
                    <StatusBadge status={t.status} size="sm" />
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-zinc-500">No support tickets found.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
