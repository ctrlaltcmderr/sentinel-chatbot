import React, { useState, useEffect } from 'react';
import {
  Sliders,
  Clock,
  Shield,
  Languages,
  CheckCircle,
  Save,
  RotateCcw,
  Zap,
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
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground tracking-tight">System Administration</h1>
          <p className="text-xs text-muted-foreground">
            Configure business hours, SLA response thresholds, escalation rules, and session limits.
          </p>
        </div>
        {savedSuccess && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-semibold animate-fade-in">
            <CheckCircle className="w-4 h-4" />
            <span>Settings Saved & Applied in Real-Time</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6 text-xs">
        {/* Business Hours & After-Hours Configuration */}
        <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">Operating Business Hours</h2>
          </div>
          <p className="text-xs text-muted-foreground">
            Inquiries outside these hours are triaged: urgent issues route to the On-Call Queue, normal complaints schedule for next business day.
          </p>

          <div className="grid grid-cols-2 gap-4 pt-2">
            <div className="space-y-1">
              <label className="font-semibold text-foreground">Start Hour (24h format):</label>
              <input
                type="number"
                min={0}
                max={23}
                value={bhStart}
                onChange={(e) => setBhStart(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground font-mono text-xs"
              />
              <span className="text-[10px] text-muted-foreground">Default: 09:00 AM</span>
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-foreground">End Hour (24h format):</label>
              <input
                type="number"
                min={0}
                max={23}
                value={bhEnd}
                onChange={(e) => setBhEnd(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground font-mono text-xs"
              />
              <span className="text-[10px] text-muted-foreground">Default: 18:00 PM (6:00 PM)</span>
            </div>
          </div>
        </div>

        {/* SLA Response Rules */}
        <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">SLA Response Windows (Business Hours)</h2>
          </div>
          <p className="text-xs text-muted-foreground">
            SLA deadlines automatically exclude configured weekends and statutory holidays, issuing warnings at 75% elapsed.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
            <div className="space-y-1">
              <label className="font-semibold text-rose-500">Critical Priority (Hours):</label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                value={criticalSla}
                onChange={(e) => setCriticalSla(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground font-mono text-xs"
              />
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-orange-500">High Priority (Hours):</label>
              <input
                type="number"
                step="0.5"
                min="1"
                value={highSla}
                onChange={(e) => setHighSla(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground font-mono text-xs"
              />
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-amber-500">Medium Priority (Hours):</label>
              <input
                type="number"
                step="1"
                min="1"
                value={mediumSla}
                onChange={(e) => setMediumSla(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground font-mono text-xs"
              />
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-slate-500">Low Priority (Hours):</label>
              <input
                type="number"
                step="1"
                min="1"
                value={lowSla}
                onChange={(e) => setLowSla(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground font-mono text-xs"
              />
            </div>
          </div>
        </div>

        {/* Escalation & Session Limits */}
        <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">Escalation & Session Parameters</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            <div className="space-y-1">
              <label className="font-semibold text-foreground">Repeated Negative Threshold:</label>
              <input
                type="number"
                min={2}
                max={10}
                value={negativeThreshold}
                onChange={(e) => setNegativeThreshold(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground font-mono text-xs"
              />
              <span className="text-[10px] text-muted-foreground">Consecutive negative/frustrated messages (default: 3)</span>
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-foreground">Unresolved Timeout (Minutes):</label>
              <input
                type="number"
                min={5}
                max={60}
                value={unresolvedTimeout}
                onChange={(e) => setUnresolvedTimeout(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground font-mono text-xs"
              />
              <span className="text-[10px] text-muted-foreground">Negative conversation auto-escalation (default: 15m)</span>
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-foreground">Session Inactivity Timeout (Minutes):</label>
              <input
                type="number"
                min={10}
                max={120}
                value={sessionTimeout}
                onChange={(e) => setSessionTimeout(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground font-mono text-xs"
              />
              <span className="text-[10px] text-muted-foreground">Inactivity close window (default: 30m, restore &lt; 24h)</span>
            </div>
          </div>
        </div>

        {/* Read-Only System Architecture Metadata */}
        <div className="p-6 rounded-xl bg-muted/30 border border-border space-y-3">
          <div className="flex items-center gap-2">
            <Languages className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-bold text-foreground uppercase tracking-wider">
              Connected Subsystems & Security Architecture
            </h3>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1 text-[11px]">
            <div className="p-2.5 rounded-lg bg-card border border-border">
              <span className="text-muted-foreground block">Languages:</span>
              <span className="font-semibold text-foreground uppercase">
                {settings?.supported_languages?.join(', ') || 'EN, ES, FR, HI'}
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-card border border-border">
              <span className="text-muted-foreground block">RBAC Tiers:</span>
              <span className="font-semibold text-foreground capitalize">
                {settings?.access_levels?.join(', ') || 'Public, Internal, Restricted, Confidential'}
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-card border border-border">
              <span className="text-muted-foreground block">Maintenance Window:</span>
              <span className="font-semibold text-foreground">01:00 AM – 05:00 AM</span>
            </div>
            <div className="p-2.5 rounded-lg bg-card border border-border">
              <span className="text-muted-foreground block">Quality Gate Thresholds:</span>
              <span className="font-semibold text-foreground">Accuracy ≥ 85%, Grounding ≥ 80%</span>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-xs shadow-sm hover:opacity-95 transition-opacity disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Applying Settings...' : 'Save Configuration Changes'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};

