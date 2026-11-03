import React, { useState, useEffect } from 'react';
import {
  Sliders,
  Clock,
  Shield,
  Zap,
  CheckCircle,
  Save,
} from 'lucide-react';
import { api } from '../api/client';
import { AdminSettings } from '../types';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Editable form fields
  const [bhStart, setBhStart] = useState(9);
  const [bhEnd, setBhEnd] = useState(18);
  const [criticalSla, setCriticalSla] = useState(1.0);
  const [highSla, setHighSla] = useState(4.0);
  const [mediumSla, setMediumSla] = useState(8.0);
  const [lowSla, setLowSla] = useState(24.0);
  const [negativeThreshold, setNegativeThreshold] = useState(3);
  const [unresolvedTimeout, setUnresolvedTimeout] = useState(15);
  const [sessionTimeout, setSessionTimeout] = useState(30);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await api.getAdminSettings();
      setSettings(data);
      setBhStart(data.business_hours_start);
      setBhEnd(data.business_hours_end);
      setCriticalSla(data.sla_hours.critical || 1.0);
      setHighSla(data.sla_hours.high || 4.0);
      setMediumSla(data.sla_hours.medium || 8.0);
      setLowSla(data.sla_hours.low || 24.0);
      setNegativeThreshold(data.escalation_negative_count);
      setUnresolvedTimeout(data.unresolved_escalation_minutes);
      setSessionTimeout(data.session_timeout_minutes);
    } catch (err) {
      console.error('Failed to load admin settings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      setSavedSuccess(false);
      const updated = await api.updateAdminSettings({
        business_hours_start: Number(bhStart),
        business_hours_end: Number(bhEnd),
        sla_hours: {
          critical: Number(criticalSla),
          high: Number(highSla),
          medium: Number(mediumSla),
          low: Number(lowSla),
        },
        escalation_negative_count: Number(negativeThreshold),
        unresolved_escalation_minutes: Number(unresolvedTimeout),
        session_timeout_minutes: Number(sessionTimeout),
      });
      setSettings(updated);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to update settings:', err);
    } finally {
      setSaving(false);
    }
  };

  if (loading && !settings) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="w-6 h-6 border-2 border-zinc-500 border-t-zinc-200 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100 tracking-tight">System Administration & Operational Policies</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Configure business hours, SLA response thresholds, escalation triggers, and session timeouts.
          </p>
        </div>
        {savedSuccess && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>Applied in Real-Time</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6 text-xs">
        {/* Operating Business Hours */}
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                Operating Business Hours (EST / Local)
              </h2>
              <p className="text-[11px] text-zinc-500 mt-0.5">
                Inquiries outside these hours are triaged: urgent queries route to on-call duty, standard complaints hold for next business day.
              </p>
            </div>
            <Clock className="w-4 h-4 text-zinc-500 shrink-0" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-zinc-400 font-medium text-[11px] uppercase tracking-wider block">
                Start Hour (24h format)
              </label>
              <input
                type="number"
                min={0}
                max={23}
                value={bhStart}
                onChange={(e) => setBhStart(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 font-mono text-xs focus:outline-none focus:border-zinc-500"
              />
              <span className="text-[10px] text-zinc-500 font-mono">09:00 AM standard</span>
            </div>

            <div className="space-y-1">
              <label className="text-zinc-400 font-medium text-[11px] uppercase tracking-wider block">
                End Hour (24h format)
              </label>
              <input
                type="number"
                min={0}
                max={23}
                value={bhEnd}
                onChange={(e) => setBhEnd(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 font-mono text-xs focus:outline-none focus:border-zinc-500"
              />
              <span className="text-[10px] text-zinc-500 font-mono">18:00 PM standard (6:00 PM)</span>
            </div>
          </div>
        </div>

        {/* SLA Windows */}
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                SLA Response Deadlines (Business Hours)
              </h2>
              <p className="text-[11px] text-zinc-500 mt-0.5">
                SLA deadlines skip weekends and holidays automatically, triggering supervisor alerts at 75% elapsed.
              </p>
            </div>
            <Zap className="w-4 h-4 text-zinc-500 shrink-0" />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="space-y-1">
              <label className="text-red-400 font-mono text-[11px] uppercase tracking-wider block">
                Critical Priority
              </label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                value={criticalSla}
                onChange={(e) => setCriticalSla(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 font-mono text-xs focus:outline-none focus:border-zinc-500"
              />
              <span className="text-[10px] text-zinc-500 font-mono">Hours (e.g. 1.0h)</span>
            </div>

            <div className="space-y-1">
              <label className="text-amber-400 font-mono text-[11px] uppercase tracking-wider block">
                High Priority
              </label>
              <input
                type="number"
                step="0.5"
                min="1"
                value={highSla}
                onChange={(e) => setHighSla(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 font-mono text-xs focus:outline-none focus:border-zinc-500"
              />
              <span className="text-[10px] text-zinc-500 font-mono">Hours (e.g. 4.0h)</span>
            </div>

            <div className="space-y-1">
              <label className="text-zinc-300 font-mono text-[11px] uppercase tracking-wider block">
                Medium Priority
              </label>
              <input
                type="number"
                step="1"
                min="1"
                value={mediumSla}
                onChange={(e) => setMediumSla(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 font-mono text-xs focus:outline-none focus:border-zinc-500"
              />
              <span className="text-[10px] text-zinc-500 font-mono">Hours (e.g. 8.0h)</span>
            </div>

            <div className="space-y-1">
              <label className="text-zinc-500 font-mono text-[11px] uppercase tracking-wider block">
                Low Priority
              </label>
              <input
                type="number"
                step="1"
                min="1"
                value={lowSla}
                onChange={(e) => setLowSla(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 font-mono text-xs focus:outline-none focus:border-zinc-500"
              />
              <span className="text-[10px] text-zinc-500 font-mono">Hours (e.g. 24.0h)</span>
            </div>
          </div>
        </div>

        {/* Escalation & Session Limits */}
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                Escalation Thresholds & Session Lifecycle
              </h2>
              <p className="text-[11px] text-zinc-500 mt-0.5">
                Controls consecutive negative emotion triggers and session memory expiration.
              </p>
            </div>
            <Shield className="w-4 h-4 text-zinc-500 shrink-0" />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1">
              <label className="text-zinc-400 font-medium text-[11px] uppercase tracking-wider block">
                Negative Escalation Count
              </label>
              <input
                type="number"
                min={1}
                max={10}
                value={negativeThreshold}
                onChange={(e) => setNegativeThreshold(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 font-mono text-xs focus:outline-none focus:border-zinc-500"
              />
              <span className="text-[10px] text-zinc-500">Consecutive negative customer inputs</span>
            </div>

            <div className="space-y-1">
              <label className="text-zinc-400 font-medium text-[11px] uppercase tracking-wider block">
                Unresolved Case Timeout
              </label>
              <input
                type="number"
                min={5}
                max={120}
                value={unresolvedTimeout}
                onChange={(e) => setUnresolvedTimeout(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 font-mono text-xs focus:outline-none focus:border-zinc-500"
              />
              <span className="text-[10px] text-zinc-500">Minutes before supervisor escalation</span>
            </div>

            <div className="space-y-1">
              <label className="text-zinc-400 font-medium text-[11px] uppercase tracking-wider block">
                Session Inactivity Window
              </label>
              <input
                type="number"
                min={5}
                max={180}
                value={sessionTimeout}
                onChange={(e) => setSessionTimeout(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 font-mono text-xs focus:outline-none focus:border-zinc-500"
              />
              <span className="text-[10px] text-zinc-500">Minutes before session memory cleanup</span>
            </div>
          </div>
        </div>

        {/* Save Bar */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 rounded bg-zinc-100 text-zinc-950 hover:bg-white text-xs font-medium transition-colors shadow-sm disabled:opacity-50 flex items-center gap-1.5"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? 'Updating Settings...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
