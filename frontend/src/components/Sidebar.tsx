import React from 'react';
import {
  LayoutDashboard,
  MessageSquare,
  Ticket,
  BookOpen,
  BarChart3,
  Sliders,
  Shield,
  Moon,
  Sun,
  Activity,
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
    <aside className="w-64 bg-card border-r border-border flex flex-col justify-between shrink-0 h-screen select-none">
      {/* Brand Header */}
      <div>
        <div className="h-16 px-6 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shadow-sm">
              <Shield className="w-5 h-5 text-primary" />
            </div>
            <div>
              <span className="font-bold text-sm tracking-wider text-foreground">SENTINEL</span>
              <span className="block text-[10px] text-muted-foreground uppercase font-medium tracking-widest">
                Support SaaS
              </span>
            </div>
          </div>
          <span className="text-[10px] px-2 py-0.5 font-semibold bg-primary/10 text-primary border border-primary/20 rounded-md">
            v2.0
          </span>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  active
                    ? 'bg-primary text-primary-foreground shadow-sm shadow-primary/20'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${active ? 'text-primary-foreground' : 'text-muted-foreground'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                      active ? 'bg-primary-foreground/20 text-primary-foreground' : 'bg-primary/15 text-primary'
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
      <div className="p-4 border-t border-border space-y-3">
        <div className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-muted/40 border border-border/50 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-muted-foreground font-medium">Engine Active</span>
          </div>
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold uppercase">
            6 Subsystems
          </span>
        </div>

        <button
          onClick={onToggleTheme}
          className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors border border-transparent hover:border-border"
        >
          <div className="flex items-center gap-2.5">
            {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
            <span>{isDark ? 'Light Theme' : 'Dark Theme'}</span>
          </div>
          <span className="text-[10px] text-muted-foreground font-mono">⌘T</span>
        </button>
      </div>
    </aside>
  );
};

