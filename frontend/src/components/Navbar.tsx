import React from 'react';
import { Search, Bell, ShieldCheck, User } from 'lucide-react';

interface Props {
  title: string;
  subtitle?: string;
  onSearchChange?: (term: string) => void;
}

export const Navbar: React.FC<Props> = ({ title, subtitle }) => {
  return (
    <header className="h-16 px-8 border-b border-border bg-card/50 backdrop-blur-md flex items-center justify-between shrink-0">
      <div>
        <h1 className="text-base font-semibold text-foreground tracking-tight">{title}</h1>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted/40 border border-border text-xs text-muted-foreground">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
          <span>RBAC: Tier Public/Admin</span>
        </div>

        <div className="flex items-center gap-2.5 pl-3 border-l border-border">
          <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-semibold text-xs">
            SA
          </div>
          <div className="hidden md:block text-left text-xs">
            <span className="font-medium text-foreground block">Support Lead</span>
            <span className="text-[10px] text-muted-foreground block">Operations Agent</span>
          </div>
        </div>
      </div>
    </header>
  );
};

