import React, { useEffect, useState } from 'react';
import {
  MessageSquare,
  Ticket,
  AlertTriangle,
  Clock,
  TrendingUp,
  CheckCircle2,
  ShieldAlert,
  ArrowRight,
  Flame,
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
      setRecentConversations(convs.slice(0, 5));
      setRecentTickets(tkts.slice(0, 5));
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
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-muted-foreground font-medium">Aggregating operational intelligence...</span>
        </div>
      </div>
    );
  }

  const statCards = [
    {
      label: 'Total Inquiries',
      value: overview?.total_conversations || 0,
      sub: `${overview?.active_conversations || 0} active currently`,
      icon: MessageSquare,
      color: 'text-blue-500 bg-blue-500/10 border-blue-500/20',
    },
    {
      label: 'Support Tickets',
      value: overview?.total_tickets || 0,
      sub: `${overview?.open_tickets || 0} open & in-progress`,
      icon: Ticket,
      color: 'text-indigo-500 bg-indigo-500/10 border-indigo-500/20',
    },
    {
      label: 'Escalated Cases',
      value: overview?.escalated_conversations || 0,
      sub: 'Multi-subsystem escalations',
      icon: AlertTriangle,
      color: 'text-orange-500 bg-orange-500/10 border-orange-500/20',
    },
    {
      label: 'High-Risk Incidents',
      value: overview?.high_risk_incidents || 0,
      sub: 'Compromise & fraud alerts',
      icon: ShieldAlert,
      color: 'text-rose-500 bg-rose-500/10 border-rose-500/20',
    },
    {
      label: 'Resolved Tickets',
      value: overview?.resolved_tickets || 0,
      sub: 'Closed inquiries',
      icon: CheckCircle2,
      color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20',
    },
    {
      label: 'Avg Response Latency',
      value: `${overview?.average_response_time_ms || 45} ms`,
      sub: 'Deterministic processing',
      icon: Clock,
      color: 'text-purple-500 bg-purple-500/10 border-purple-500/20',
    },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {statCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              className="p-4 rounded-xl bg-card border border-border hover:border-border/80 transition-all shadow-sm flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground font-medium">{card.label}</span>
                <div className={`p-2 rounded-lg border ${card.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-bold text-foreground tracking-tight">{card.value}</div>
                <div className="text-[11px] text-muted-foreground mt-0.5">{card.sub}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Visual Charts & Breakdowns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 7-Day Inbound Activity Timeline */}
        <div className="lg:col-span-2 p-6 rounded-xl bg-card border border-border shadow-sm space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Conversation Activity Timeline</h2>
              <p className="text-xs text-muted-foreground">Inbound customer conversations vs escalations (past 7 days)</p>
            </div>
            <div className="flex items-center gap-4 text-xs font-medium">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span className="w-2.5 h-2.5 rounded-sm bg-primary" /> Total
              </span>
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span className="w-2.5 h-2.5 rounded-sm bg-rose-500" /> Escalated
              </span>
            </div>
          </div>

          {/* SVG Bar Chart */}
          <div className="h-56 flex items-end justify-between gap-3 pt-6 border-b border-border/60 pb-3">
            {trends?.activity_timeline && trends.activity_timeline.length > 0 ? (
              trends.activity_timeline.map((item, idx) => {
                const maxVal = Math.max(
                  ...trends.activity_timeline.map((t) => t.conversations),
                  5
                );
                const convHeight = Math.max((item.conversations / maxVal) * 100, 6);
                const escHeight = Math.max((item.escalations / maxVal) * 100, item.escalations > 0 ? 8 : 0);

                return (
                  <div key={idx} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
                    <div className="w-full flex items-end justify-center gap-1.5 h-full">
                      {/* Conversations bar */}
                      <div
                        style={{ height: `${convHeight}%` }}
                        className="w-1/2 max-w-[28px] bg-primary/80 group-hover:bg-primary rounded-t-md transition-all relative flex justify-center"
                      >
                        <span className="opacity-0 group-hover:opacity-100 absolute -top-6 text-[10px] font-semibold text-foreground transition-opacity">
                          {item.conversations}
                        </span>
                      </div>
                      {/* Escalation bar */}
                      <div
                        style={{ height: `${escHeight}%` }}
                        className="w-1/2 max-w-[28px] bg-rose-500/80 group-hover:bg-rose-500 rounded-t-md transition-all relative flex justify-center"
                      >
                        {item.escalations > 0 && (
                          <span className="opacity-0 group-hover:opacity-100 absolute -top-6 text-[10px] font-semibold text-rose-500 transition-opacity">
                            {item.escalations}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="text-[10px] font-medium text-muted-foreground">
                      {item.date.slice(5)}
                    </span>
                  </div>
                );
              })
            ) : (
              <div className="w-full h-full flex items-center justify-center text-xs text-muted-foreground">
                No activity data available.
              </div>
            )}
          </div>

          <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
            <span>Aggregated automatically from live database interactions</span>
            <button
              onClick={() => onNavigate('analytics')}
              className="text-primary hover:underline font-medium flex items-center gap-1"
            >
              Full Analytics <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Sentiment Distribution */}
        <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-5">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Sentiment Breakdown</h2>
            <p className="text-xs text-muted-foreground">Multi-class classification distribution</p>
          </div>

          <div className="space-y-3 pt-1">
            {trends?.sentiment_counts &&
              Object.entries(trends.sentiment_counts).map(([sentiment, count]) => {
                const total = Math.max(
                  Object.values(trends.sentiment_counts).reduce((a, b) => a + b, 0),
                  1
                );
                const percent = Math.round((count / total) * 100);

                return (
                  <div key={sentiment} className="space-y-1">
                    <div className="flex items-center justify-between text-xs font-medium">
                      <span className="capitalize text-foreground flex items-center gap-1.5">
                        <SentimentBadge sentiment={sentiment} size="sm" />
                      </span>
                      <span className="text-muted-foreground">
                        {count} ({percent}%)
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        style={{ width: `${percent}%` }}
                        className={`h-full rounded-full transition-all duration-300 ${
                          sentiment === 'positive'
                            ? 'bg-emerald-500'
                            : sentiment === 'frustrated'
                            ? 'bg-orange-500'
                            : sentiment === 'urgent'
                            ? 'bg-rose-500'
                            : sentiment === 'sarcastic'
                            ? 'bg-purple-500'
                            : sentiment === 'negative'
                            ? 'bg-amber-500'
                            : 'bg-sky-500'
                        }`}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      </div>

      {/* Recent Tables: Escalations and Tickets */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Conversations */}
        <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Recent Customer Conversations</h2>
              <p className="text-xs text-muted-foreground">Live sentiment and escalation status</p>
            </div>
            <button
              onClick={() => onNavigate('chat')}
              className="text-xs font-medium text-primary hover:underline flex items-center gap-1"
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
                  className="py-3 flex items-center justify-between gap-3 hover:bg-muted/40 px-2 rounded-lg cursor-pointer transition-colors"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-foreground truncate">{c.title}</span>
                      {c.is_high_risk && (
                        <span className="text-[10px] font-bold text-rose-500 uppercase bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20">
                          High Risk
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      <span>{c.customer_name || c.customer_id}</span>
                      <span>•</span>
                      <span>{new Date(c.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                  <div className="shrink-0">
                    <SentimentBadge sentiment={c.last_sentiment} confidence={c.last_confidence} size="sm" />
                  </div>
                </div>
              ))
            ) : (
              <div className="py-6 text-center text-xs text-muted-foreground">No recent conversations recorded.</div>
            )}
          </div>
        </div>

        {/* Recent Tickets */}
        <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Recent Support Tickets</h2>
              <p className="text-xs text-muted-foreground">SLA deadlines and team routing</p>
            </div>
            <button
              onClick={() => onNavigate('tickets')}
              className="text-xs font-medium text-primary hover:underline flex items-center gap-1"
            >
              Manage Tickets <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-border/60">
            {recentTickets.length > 0 ? (
              recentTickets.map((t) => (
                <div
                  key={t.id}
                  onClick={() => onNavigate('tickets')}
                  className="py-3 flex items-center justify-between gap-3 hover:bg-muted/40 px-2 rounded-lg cursor-pointer transition-colors"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-semibold text-primary">#{t.id.slice(0, 8)}</span>
                      <span className="text-xs text-foreground truncate">{t.issue_description}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      <span className="capitalize">{t.assigned_team} Team</span>
                      <span>•</span>
                      <span>Priority: <span className="capitalize font-medium text-foreground">{t.priority}</span></span>
                      {t.sla_breached && (
                        <span className="text-rose-500 font-semibold">• SLA BREACHED</span>
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
              <div className="py-6 text-center text-xs text-muted-foreground">No support tickets found.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

