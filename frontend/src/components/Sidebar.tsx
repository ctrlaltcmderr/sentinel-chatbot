import React from 'react';
import {
  LayoutDashboard,
  MessageSquare,
  Ticket,
  BookOpen,
  BarChart3,
  Sliders,
  Moon,
  Sun,
  Shield,
  Circle,
} from 'lucide-react';

interface Props {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  isDark: boolean;
  onToggleTheme: () => void;
  openTicketsCount?: number;
}

export const Sidebar: React.FC<Props> = ({
  currentTab,
  onSelectTab,
  isDark,
  onToggleTheme,
  openTicketsCount = 0,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
    { id: 'chat', label: 'Live Chat', icon: MessageSquare },
    { id: 'tickets', label: 'Tickets', icon: Ticket, badge: openTicketsCount > 0 ? openTicketsCount : null },
    { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'settings', label: 'Administration', icon: Sliders },
  ];

  return (
    <aside className="w-60 bg-surface-950 dark:bg-[#0c0c0e] border-r border-border flex flex-col justify-between shrink-0 h-screen select-none">
      {/* Brand & Organization Header */}
      <div>
        <div className="h-14 px-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md bg-zinc-800 border border-zinc-700/70 flex items-center justify-center text-zinc-100 shadow-sm">
              <Shield className="w-4 h-4 text-zinc-200" strokeWidth={2.2} />
            </div>
            <div>
              <span className="font-semibold text-xs tracking-wider text-zinc-100 uppercase">Sentinel</span>
              <span className="block text-[10px] text-zinc-500 font-mono tracking-tight leading-none">
                Support SaaS
              </span>
            </div>
          </div>
          <span className="text-[10px] font-mono px-1.5 py-0.5 text-zinc-400 bg-zinc-800/80 border border-zinc-700/50 rounded">
            v2.0
          </span>
        </div>

        {/* Section Label */}
        <div className="px-4 pt-4 pb-1.5">
          <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium">Workspace</span>
        </div>

        {/* Navigation Links */}
        <nav className="px-2 space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-[13px] transition-all group ${
                  active
                    ? 'bg-zinc-800/90 text-zinc-100 font-medium border border-white/[0.06] shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40 font-normal'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon
                    className={`w-4 h-4 shrink-0 transition-colors ${
                      active ? 'text-zinc-100' : 'text-zinc-400 group-hover:text-zinc-200'
                    }`}
                    strokeWidth={1.75}
                  />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded tabular-nums ${
                      active
                        ? 'bg-zinc-700 text-zinc-200'
                        : 'bg-zinc-800/80 text-zinc-400 border border-zinc-700/50'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Controls & System Status */}
      <div className="p-3 border-t border-border space-y-2">
        <div className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-zinc-900/60 border border-zinc-800/60 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span className="text-[11px] text-zinc-400 font-medium">Engine Active</span>
          </div>
          <span className="text-[10px] font-mono text-zinc-500">6/6 Systems</span>
        </div>

        <button
          onClick={onToggleTheme}
          className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-[12px] text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40 transition-colors"
        >
          <div className="flex items-center gap-2">
            {isDark ? (
              <Sun className="w-3.5 h-3.5 text-zinc-400" strokeWidth={1.75} />
            ) : (
              <Moon className="w-3.5 h-3.5 text-zinc-400" strokeWidth={1.75} />
            )}
            <span>{isDark ? 'Light Mode' : 'Dark Mode'}</span>
          </div>
          <span className="text-[10px] font-mono text-zinc-500 border border-zinc-800 px-1 rounded">⌘T</span>
        </button>
      </div>
    </aside>
  );
};
