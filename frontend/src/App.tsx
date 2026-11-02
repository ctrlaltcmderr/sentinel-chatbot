import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { ChatPage } from './pages/ChatPage';
import { TicketsPage } from './pages/TicketsPage';
import { KnowledgePage } from './pages/KnowledgePage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SettingsPage } from './pages/SettingsPage';
import { api } from './api/client';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [isDark, setIsDark] = useState<boolean>(() => {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  const [openTicketsCount, setOpenTicketsCount] = useState<number>(0);

  // Sync theme class
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  // Keyboard shortcut to toggle theme
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 't') {
        e.preventDefault();
        setIsDark((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Poll open tickets count for sidebar badge
  useEffect(() => {
    const fetchBadge = async () => {
      try {
        const ov = await api.getAnalyticsOverview();
        setOpenTicketsCount(ov.open_tickets);
      } catch {
        // ignore
      }
    };
    fetchBadge();
  }, [currentTab]);

  const handleNavigate = (tab: string, sessionId?: string) => {
    if (sessionId) {
      setSelectedSessionId(sessionId);
    }
    setCurrentTab(tab);
  };

  const getPageInfo = () => {
    switch (currentTab) {
      case 'chat':
        return {
          title: 'Customer Support Chatbot',
          subtitle: 'Live session with multilingual sentiment, RAG citations & multimodal OCR',
        };
      case 'tickets':
        return {
          title: 'Support Tickets & Routing',
          subtitle: 'Priority scoring, calendar-aware SLA management, and agent workload routing',
        };
      case 'knowledge':
        return {
          title: 'Knowledge Base Pipeline',
          subtitle: 'Temporal policy indexing, automated quality gates, and quarantine protection',
        };
      case 'analytics':
        return {
          title: 'Operational Telemetry',
          subtitle: 'Real-time performance analytics, sentiment trends, and language distributions',
        };
      case 'settings':
        return {
          title: 'System Administration',
          subtitle: 'Business hours, SLA windows, escalation thresholds, and runtime controls',
        };
      case 'dashboard':
      default:
        return {
          title: 'Operations Dashboard',
          subtitle: 'Unified enterprise customer support overview & intelligence',
        };
    }
  };

  const pageInfo = getPageInfo();

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans">
      {/* Permanent Left Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={(tab) => {
          setSelectedSessionId(null);
          setCurrentTab(tab);
        }}
        isDark={isDark}
        onToggleTheme={() => setIsDark(!isDark)}
        openTicketsCount={openTicketsCount}
      />

      {/* Main View Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Navbar
          title={pageInfo.title}
          subtitle={pageInfo.subtitle}
        />

        <main className="flex-1 overflow-y-auto bg-background">
          {currentTab === 'dashboard' && (
            <DashboardPage onNavigate={handleNavigate} />
          )}
          {currentTab === 'chat' && (
            <ChatPage
              initialSessionId={selectedSessionId}
              onNavigateToTicket={() => setCurrentTab('tickets')}
            />
          )}
          {currentTab === 'tickets' && <TicketsPage />}
          {currentTab === 'knowledge' && <KnowledgePage />}
          {currentTab === 'analytics' && <AnalyticsPage />}
          {currentTab === 'settings' && <SettingsPage />}
        </main>
      </div>
    </div>
  );
};

