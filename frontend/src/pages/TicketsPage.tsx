import React, { useState, useEffect } from 'react';
import {
  Ticket as TicketIcon,
  Search,
  Clock,
  User,
  Send,
  ShieldAlert,
  X,
  FileText,
  Filter,
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
      const freshTicket = await api.getTicket(selectedTicket.id);
      setSelectedTicket(freshTicket);
      setTickets((prev) => prev.map((t) => (t.id === freshTicket.id ? freshTicket : t)));
    } catch (err) {
      console.error('Failed to add note:', err);
    } finally {
      setSubmittingNote(false);
    }
  };

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100 tracking-tight">Support Tickets & SLA Queue</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Operational triage, multi-agent workload dispatching, and calendar-aware business SLA tracking.
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs text-zinc-400">
          <span className="tabular-nums font-semibold text-zinc-200">{tickets.length}</span> tickets loaded
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="p-3 rounded-lg border border-border bg-card">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-zinc-500" />
            <input
              type="text"
              placeholder="Search by ID, customer, issue..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-md bg-zinc-900 border border-border text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-500 transition-colors"
            />
          </div>

          {/* Status Filter */}
          <div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-md bg-zinc-900 border border-border text-xs text-zinc-200 focus:outline-none focus:border-zinc-500 transition-colors"
            >
              <option value="all">All Statuses</option>
              <option value="Open">Open</option>
              <option value="In Progress">In Progress</option>
              <option value="Pending">Pending</option>
              <option value="Escalated">Escalated</option>
              <option value="Resolved">Resolved</option>
              <option value="Closed">Closed</option>
            </select>
          </div>

          {/* Priority Filter */}
          <div>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-md bg-zinc-900 border border-border text-xs text-zinc-200 focus:outline-none focus:border-zinc-500 transition-colors"
            >
              <option value="all">All Priorities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Team Filter */}
          <div>
            <select
              value={teamFilter}
              onChange={(e) => setTeamFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-md bg-zinc-900 border border-border text-xs text-zinc-200 focus:outline-none focus:border-zinc-500 transition-colors"
            >
              <option value="all">All Teams</option>
              <option value="billing">Billing Team</option>
              <option value="technical">Technical Team</option>
              <option value="account_security">Account Security</option>
              <option value="shipping">Shipping Team</option>
              <option value="general">General Support</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tickets Table */}
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-900/70 border-b border-border text-zinc-400 uppercase text-[10px] tracking-wider font-medium">
              <tr>
                <th className="px-4 py-3">Ticket ID</th>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Issue Description</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Assigned Team</th>
                <th className="px-4 py-3">SLA Deadline</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {tickets.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => setSelectedTicket(t)}
                  className="hover:bg-zinc-900/50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-zinc-300">
                    #{t.id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-zinc-200">{t.customer_name || t.customer_id}</div>
                    <div className="text-[10px] text-zinc-500">{t.contact_email || 'No email provided'}</div>
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate text-zinc-300">
                    {t.issue_description}
                  </td>
                  <td className="px-4 py-3">
                    <PriorityBadge priority={t.priority} size="sm" />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={t.status} size="sm" />
                  </td>
                  <td className="px-4 py-3 capitalize font-medium text-zinc-300">
                    {t.assigned_team}
                  </td>
                  <td className="px-4 py-3">
                    {t.sla_deadline ? (
                      <div className="space-y-0.5">
                        <span
                          className={`font-mono ${
                            t.sla_breached ? 'text-red-400 font-semibold' : 'text-zinc-300'
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
                          <div className="text-[10px] text-red-400 font-mono font-bold tracking-tight">
                            BREACHED
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className="text-zinc-500 font-mono text-[11px]">Standard</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedTicket(t);
                      }}
                      className="px-2.5 py-1 rounded border border-border text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors text-[11px] font-medium"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
              {tickets.length === 0 && !loading && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-zinc-500 text-xs font-mono">
                    No tickets match the selected query and filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ticket Details Modal / Drawer */}
      {selectedTicket && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl bg-card border border-border rounded-lg shadow-xl overflow-hidden max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-zinc-900/50">
              <div className="flex items-center gap-2.5">
                <TicketIcon className="w-4 h-4 text-zinc-400" />
                <div>
                  <h3 className="text-sm font-semibold text-zinc-100">
                    Ticket #{selectedTicket.id.slice(0, 8)}
                  </h3>
                  <p className="text-[10px] text-zinc-500 font-mono">{selectedTicket.id}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedTicket(null)}
                className="p-1.5 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-5 text-xs">
              {/* Breach Banner if SLA violated */}
              {selectedTicket.sla_breached && (
                <div className="p-3 rounded-md bg-red-500/10 border border-red-500/20 text-red-400 font-medium flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 shrink-0" />
                  <span>SLA Breached: Automatic escalation dispatched to on-call duty supervisor.</span>
                </div>
              )}

              {/* Status and Team Assignment Row */}
              <div className="grid grid-cols-2 gap-4 p-4 rounded-md bg-zinc-900/60 border border-border">
                <div className="space-y-1.5">
                  <span className="text-zinc-400 font-medium block text-[11px] uppercase tracking-wider">Ticket Status</span>
                  <select
                    value={selectedTicket.status}
                    onChange={(e) =>
                      handleStatusChange(selectedTicket.id, e.target.value as TicketStatus)
                    }
                    className="w-full px-2.5 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 font-medium text-xs focus:outline-none focus:border-zinc-500"
                  >
                    <option value="Open">Open</option>
                    <option value="In Progress">In Progress</option>
                    <option value="Pending">Pending</option>
                    <option value="Escalated">Escalated</option>
                    <option value="Resolved">Resolved</option>
                    <option value="Closed">Closed</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <span className="text-zinc-400 font-medium block text-[11px] uppercase tracking-wider">Assigned Team</span>
                  <select
                    value={selectedTicket.assigned_team}
                    onChange={(e) => handleTeamChange(selectedTicket.id, e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 font-medium text-xs capitalize focus:outline-none focus:border-zinc-500"
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
                <h4 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                  Customer & Incident Context
                </h4>
                <div className="grid grid-cols-2 gap-3 p-4 rounded-md bg-zinc-900/40 border border-border">
                  <div>
                    <span className="text-zinc-500 text-[11px]">Customer:</span>
                    <div className="font-medium text-zinc-200 mt-0.5">
                      {selectedTicket.customer_name || selectedTicket.customer_id}
                    </div>
                  </div>
                  <div>
                    <span className="text-zinc-500 text-[11px]">Contact Email:</span>
                    <div className="font-medium text-zinc-200 mt-0.5">
                      {selectedTicket.contact_email || 'Not provided'}
                    </div>
                  </div>
                  {selectedTicket.order_id && (
                    <div>
                      <span className="text-zinc-500 text-[11px]">Order ID:</span>
                      <div className="font-mono text-zinc-200 mt-0.5">
                        {selectedTicket.order_id}
                      </div>
                    </div>
                  )}
                  {selectedTicket.product_code && (
                    <div>
                      <span className="text-zinc-500 text-[11px]">Product Code:</span>
                      <div className="font-mono text-zinc-200 mt-0.5">
                        {selectedTicket.product_code}
                      </div>
                    </div>
                  )}
                </div>

                <div className="p-4 rounded-md bg-zinc-900/40 border border-border space-y-1">
                  <span className="text-zinc-500 text-[11px] font-medium uppercase tracking-wider block">Issue Description</span>
                  <p className="text-zinc-200 leading-relaxed font-normal">
                    {selectedTicket.issue_description}
                  </p>
                </div>

                {selectedTicket.handoff_summary && (
                  <div className="p-4 rounded-md bg-zinc-900/40 border border-border space-y-1">
                    <span className="text-zinc-500 text-[11px] font-medium uppercase tracking-wider block">
                      Autonomous Handoff Summary
                    </span>
                    <p className="text-zinc-300 leading-relaxed font-mono text-[11px] bg-zinc-950 p-2.5 rounded border border-border">
                      {selectedTicket.handoff_summary}
                    </p>
                  </div>
                )}
              </div>

              {/* Internal Notes History */}
              <div className="space-y-3">
                <h4 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                  Internal Staff Notes & Activity
                </h4>
                <div className="space-y-2">
                  {selectedTicket.notes && selectedTicket.notes.length > 0 ? (
                    selectedTicket.notes.map((note) => (
                      <div
                        key={note.id}
                        className="p-3 rounded-md bg-zinc-900/40 border border-border space-y-1"
                      >
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-medium text-zinc-300">{note.author}</span>
                          <span className="text-zinc-500 font-mono">
                            {new Date(note.created_at).toLocaleString([], {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>
                        <p className="text-zinc-300 leading-relaxed">{note.content}</p>
                      </div>
                    ))
                  ) : (
                    <div className="py-4 text-center text-zinc-500 text-[11px] font-mono">
                      No internal notes recorded yet.
                    </div>
                  )}
                </div>

                {/* Add Note Form */}
                <form onSubmit={handleAddNote} className="space-y-2 pt-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-zinc-500">Posting as:</span>
                    <input
                      type="text"
                      value={noteAuthor}
                      onChange={(e) => setNoteAuthor(e.target.value)}
                      className="px-2 py-0.5 rounded bg-zinc-900 border border-border text-xs text-zinc-200 font-medium focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                  <textarea
                    rows={3}
                    placeholder="Add an internal operations note or investigation finding..."
                    value={newNoteContent}
                    onChange={(e) => setNewNoteContent(e.target.value)}
                    className="w-full p-2.5 rounded bg-zinc-900 border border-border text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-500 transition-colors"
                  />
                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={submittingNote || !newNoteContent.trim()}
                      className="px-3 py-1.5 rounded bg-zinc-100 text-zinc-950 hover:bg-white text-xs font-medium transition-colors disabled:opacity-50 flex items-center gap-1.5"
                    >
                      <Send className="w-3 h-3" />
                      Post Note
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
