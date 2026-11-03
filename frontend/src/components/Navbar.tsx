import React from 'react';
import { Search, Shield, Command } from 'lucide-react';

interface Props {
  title: string;
  subtitle?: string;
  onSearchChange?: (term: string) => void;
}

export const Navbar: React.FC<Props> = ({ title, subtitle }) => {
  return (
    <header className="h-14 px-6 border-b border-border bg-background/80 backdrop-blur-sm flex items-center justify-between shrink-0">
      {/* Breadcrumb Hierarchy */}
      <div className="flex items-center gap-2 text-xs">
        <span className="text-zinc-500 font-medium">Sentinel</span>
        <span className="text-zinc-600">/</span>
        <span className="text-zinc-100 font-medium tracking-tight">{title}</span>
        {subtitle && (
          <>
            <span className="text-zinc-700 hidden lg:inline">•</span>
            <span className="text-zinc-500 text-[11px] hidden lg:inline font-normal">{subtitle}</span>
          </>
        )}
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Command Menu Placeholder / Quick Search */}
        <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs text-zinc-400 hover:border-zinc-700 transition-colors cursor-pointer">
          <Search className="w-3.5 h-3.5 text-zinc-500" strokeWidth={1.75} />
          <span className="text-[11px] text-zinc-400">Search cases or docs...</span>
          <kbd className="text-[10px] font-mono text-zinc-500 bg-zinc-800/80 px-1 py-0.5 rounded border border-zinc-700/60 ml-2">
            ⌘K
          </kbd>
        </div>

        {/* RBAC Scope Pill */}
        <div className="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[11px] text-zinc-400 font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span>RBAC: Tier 2 Admin</span>
        </div>

        {/* Agent Profile */}
        <div className="flex items-center gap-2 pl-3 border-l border-zinc-800/80">
          <div className="w-6 h-6 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-[10px] font-mono font-medium text-zinc-200">
            SL
          </div>
          <div className="hidden md:block text-left text-xs leading-none">
            <span className="text-[11px] font-medium text-zinc-300 block">Support Lead</span>
          </div>
        </div>
      </div>
    </header>
  );
};
