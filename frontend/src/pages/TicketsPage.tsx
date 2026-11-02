import React, { useState, useEffect } from 'react';
import {
  Ticket as TicketIcon,
  Search,
  Filter,
  Clock,
  AlertTriangle,
  User,
  Send,
  CheckCircle2,
  AlertCircle,
  X,
  FileText,
  ShieldAlert,
} from 'lucide-react';
import { api } from '../api/client';
import { Ticket, TicketPriority, TicketStatus } from '../types';
import { PriorityBadge } from '../components/PriorityBadge';
import { StatusBadge } from '../components/StatusBadge';

export const TicketsPage: React.FC = () => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [teamFilter, setTeamFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [loading, setLoading] = useState(true);

  // New note state
  const [newNoteContent, setNewNoteContent] = useState('');
  const [noteAuthor, setNoteAuthor] = useState('Support Lead');
  const [submittingNote, setSubmittingNote] = useState(false);

  const loadTickets = async () => {
    try {
      setLoading(true);
      const data = await api.getTickets({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        priority: priorityFilter !== 'all' ? priorityFilter : undefined,
        team: teamFilter !== 'all' ? teamFilter : undefined,
        search: searchQuery || undefined,
      });
      setTickets(data);
      if (selectedTicket) {
        const refreshed = data.find((t) => t.id === selectedTicket.id);
        if (refreshed) setSelectedTicket(refreshed);
      }
    } catch (err) {
      console.error('Failed to load tickets:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTickets();
  }, [statusFilter, priorityFilter, teamFilter, searchQuery]);

  const handleStatusChange = async (ticketId: string, newStatus: TicketStatus) => {
    try {
      const updated = await api.updateTicket(ticketId, { status: newStatus });
      setTickets((prev) => prev.map((t) => (t.id === ticketId ? updated : t)));
      if (selectedTicket?.id === ticketId) {
        setSelectedTicket(updated);
      }
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleTeamChange = async (ticketId: string, newTeam: string) => {
    try {
      const updated = await api.updateTicket(ticketId, { assigned_team: newTeam });
      setTickets((prev) => prev.map((t) => (t.id === ticketId ? updated : t)));
      if (selectedTicket?.id === ticketId) {
        setSelectedTicket(updated);
      }
    } catch (err) {
      console.error('Failed to update team:', err);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket || !newNoteContent.trim()) return;

    try {
      setSubmittingNote(true);
      await api.addTicketNote(selectedTicket.id, noteAuthor, newNoteContent.trim());
      setNewNoteContent('');
      // Reload ticket details
      const freshTicket = await api.getTicket(selectedTicket.id);
      setSelectedTicket(freshTicket);
      setTickets((prev) => prev.map((t) => (t.id === freshTicket.id ? freshTicket : t)));
    } catch (err) {
      console.error('Failed to add note:', err);
    } finally {
      setSubmittingNote(false);
    }
  };

  const statusTabs = ['all', 'Open', 'In Progress', 'Pending', 'Escalated', 'Resolved', 'Closed'];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground tracking-tight">Support Ticket Management</h1>
          <p className="text-xs text-muted-foreground">
            Monitor, route, and resolve customer support escalations with calendar-aware SLA tracking.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-primary/10 text-primary border border-primary/20">
            {tickets.length} Total Tickets
          </span>
        </div>
      </div>

      {/* Filter Tabs & Search Controls */}
      <div className="p-4 rounded-xl bg-card border border-border shadow-sm space-y-3">
        {/* Status Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 border-b border-border/60 pb-3">
          {statusTabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setStatusFilter(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                statusFilter === tab
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              }`}
            >
              {tab === 'all' ? 'All Tickets' : tab}
            </button>
          ))}
        </div>

        {/* Dropdown Filters and Search Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div className="sm:col-span-2 relative">
            <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ticket ID, customer, order ID, or issue..."
              className="w-full pl-8 pr-3 py-1.5 rounded-md bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-md bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="all">All Priorities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          <div>
            <select
              value={teamFilter}
              onChange={(e) => setTeamFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-md bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="all">All Teams</option>
              <option value="billing">Billing</option>
              <option value="technical">Technical</option>
              <option value="account_security">Account Security</option>
              <option value="shipping">Shipping</option>
              <option value="general">General</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tickets Table / List */}
      <div className="rounded-xl bg-card border border-border shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase text-[10px] tracking-wider font-semibold">
              <tr>
                <th className="px-4 py-3">Ticket ID</th>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Issue Description</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Team</th>
                <th className="px-4 py-3">SLA Deadline</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {tickets.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => setSelectedTicket(t)}
                  className="hover:bg-muted/40 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3.5 font-mono font-semibold text-primary">
                    #{t.id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="font-medium text-foreground">{t.customer_name || t.customer_id}</div>
                    <div className="text-[10px] text-muted-foreground">{t.contact_email || 'No email provided'}</div>
                  </td>
                  <td className="px-4 py-3.5 max-w-xs truncate text-foreground">
                    {t.issue_description}
                  </td>
                  <td className="px-4 py-3.5">
                    <PriorityBadge priority={t.priority} size="sm" />
                  </td>
                  <td className="px-4 py-3.5">
                    <StatusBadge status={t.status} size="sm" />
                  </td>
                  <td className="px-4 py-3.5 capitalize font-medium text-foreground">
                    {t.assigned_team}
                  </td>
                  <td className="px-4 py-3.5">
                    {t.sla_deadline ? (
                      <div className="space-y-0.5">
                        <span
                          className={`font-medium ${
                            t.sla_breached ? 'text-rose-500 font-bold' : 'text-foreground'
                          }`}
                        >
                          {new Date(t.sla_deadline).toLocaleString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                        {t.sla_breached && (
                          <div className="text-[10px] text-rose-500 font-bold uppercase">
                            BREACHED
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className="text-muted-foreground">Standard</span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedTicket(t);
                      }}
                      className="px-2.5 py-1 rounded-md border border-border hover:border-primary/40 text-primary font-medium hover:bg-primary/5 transition-all"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
              {tickets.length === 0 && !loading && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-muted-foreground">
                    No tickets match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ticket Details Modal / Drawer */}
      {selectedTicket && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl bg-card border border-border rounded-2xl shadow-xl overflow-hidden max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-muted/30">
              <div className="flex items-center gap-2.5">
                <TicketIcon className="w-5 h-5 text-primary" />
                <div>
                  <h3 className="text-sm font-bold text-foreground">
                    Ticket #{selectedTicket.id.slice(0, 8)}
                  </h3>
                  <p className="text-[11px] text-muted-foreground font-mono">{selectedTicket.id}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedTicket(null)}
                className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs">
              {/* Breach Banner if SLA violated */}
              {selectedTicket.sla_breached && (
                <div className="p-3 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-600 dark:text-rose-400 font-semibold flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4" />
                  <span>SLA Breached: Automatic escalation triggered to team supervisor.</span>
                </div>
              )}

              {/* Status and Team Assignment Row */}
              <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-muted/40 border border-border">
                <div className="space-y-1">
                  <span className="text-muted-foreground font-medium block">Ticket Status:</span>
                  <select
                    value={selectedTicket.status}
                    onChange={(e) =>
                      handleStatusChange(selectedTicket.id, e.target.value as TicketStatus)
                    }
                    className="w-full px-2.5 py-1.5 rounded-md bg-card border border-border text-foreground font-semibold text-xs"
                  >
                    <option value="Open">Open</option>
                    <option value="In Progress">In Progress</option>
                    <option value="Pending">Pending</option>
                    <option value="Escalated">Escalated</option>
                    <option value="Resolved">Resolved</option>
                    <option value="Closed">Closed</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <span className="text-muted-foreground font-medium block">Assigned Team:</span>
                  <select
                    value={selectedTicket.assigned_team}
                    onChange={(e) => handleTeamChange(selectedTicket.id, e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-md bg-card border border-border text-foreground font-semibold text-xs capitalize"
                  >
                    <option value="billing">Billing</option>
                    <option value="technical">Technical</option>
                    <option value="account_security">Account Security</option>
                    <option value="shipping">Shipping</option>
                    <option value="general">General</option>
                  </select>
                </div>
              </div>

              {/* Customer & Issue Information */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Inquiry Details
                </h4>
                <div className="grid grid-cols-2 gap-3 p-4 rounded-xl bg-card border border-border">
                  <div>
                    <span className="text-muted-foreground">Customer:</span>
                    <div className="font-semibold text-foreground">
                      {selectedTicket.customer_name || selectedTicket.customer_id}
                    </div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Contact Email:</span>
                    <div className="font-semibold text-foreground">
                      {selectedTicket.contact_email || 'Not provided'}
                    </div>
                  </div>
                  {selectedTicket.order_id && (
                    <div>
                      <span className="text-muted-foreground">Order ID:</span>
                      <div className="font-mono font-semibold text-foreground">
                        {selectedTicket.order_id}
                      </div>
                    </div>
                  )}
                  {selectedTicket.product_code && (
                    <div>
                      <span className="text-muted-foreground">Product Code:</span>
                      <div className="font-mono font-semibold text-foreground">
                        {selectedTicket.product_code}
                      </div>
                    </div>
                  )}
                </div>

                <div className="p-4 rounded-xl bg-card border border-border space-y-1.5">
                  <span className="text-muted-foreground font-medium">Issue Description:</span>
                  <p className="text-foreground leading-relaxed font-medium">
                    {selectedTicket.issue_description}
                  </p>
                </div>

                {selectedTicket.handoff_summary && (
                  <div className="p-4 rounded-xl bg-card border border-border space-y-1.5">
                    <span className="text-muted-foreground font-medium">
                      Masked Agent Handoff Summary:
                    </span>
                    <p className="text-foreground leading-relaxed font-mono text-[11px] bg-muted/40 p-2.5 rounded-lg border border-border">
                      {selectedTicket.handoff_summary}
                    </p>
                  </div>
                )}
              </div>

              {/* Internal Notes Timeline */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Internal Agent Notes
                </h4>

                <form onSubmit={handleAddNote} className="space-y-2">
                  <textarea
                    rows={2}
                    value={newNoteContent}
                    onChange={(e) => setNewNoteContent(e.target.value)}
                    placeholder="Add confidential internal note for the team..."
                    className="w-full p-3 rounded-lg bg-muted/40 border border-border text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <div className="flex justify-between items-center">
                    <input
                      type="text"
                      value={noteAuthor}
                      onChange={(e) => setNoteAuthor(e.target.value)}
                      placeholder="Author name"
                      className="px-2 py-1 rounded bg-muted/40 border border-border text-[11px] text-foreground w-40"
                    />
                    <button
                      type="submit"
                      disabled={!newNoteContent.trim() || submittingNote}
                      className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground font-semibold text-xs shadow-sm hover:opacity-90 disabled:opacity-50"
                    >
                      {submittingNote ? 'Saving...' : 'Post Internal Note'}
                    </button>
                  </div>
                </form>

                <div className="space-y-2">
                  {selectedTicket.notes && selectedTicket.notes.length > 0 ? (
                    selectedTicket.notes.map((note) => (
                      <div
                        key={note.id}
                        className="p-3 rounded-lg bg-muted/30 border border-border space-y-1"
                      >
                        <div className="flex justify-between text-[11px]">
                          <span className="font-semibold text-foreground">{note.author}</span>
                          <span className="text-muted-foreground">
                            {new Date(note.created_at).toLocaleString([], {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>
                        <p className="text-muted-foreground">{note.content}</p>
                      </div>
                    ))
                  ) : (
                    <div className="p-4 text-center text-muted-foreground text-xs">
                      No internal notes recorded yet.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

