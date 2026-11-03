import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Paperclip,
  Plus,
  Shield,
  User,
  AlertTriangle,
  FileText,
  CheckCircle,
  XCircle,
  HelpCircle,
  Sparkles,
  Info,
  Calendar,
  Ticket as TicketIcon,
  Search,
  ExternalLink,
  ChevronRight,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { api } from '../api/client';
import { ChatMessage, Conversation, FileInfo } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import { StatusBadge } from '../components/StatusBadge';

interface Props {
  initialSessionId?: string | null;
  onNavigateToTicket?: (ticketId: string) => void;
}

export const ChatPage: React.FC<Props> = ({ initialSessionId, onNavigateToTicket }) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>(initialSessionId || '');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [customerId, setCustomerId] = useState('cust-alex-99');
  const [accessLevel, setAccessLevel] = useState('public');
  const [referenceDate, setReferenceDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // File upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedFileInfo, setUploadedFileInfo] = useState<any | null>(null);
  const [uploading, setUploading] = useState(false);
  const [showInspector, setShowInspector] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load conversations on mount
  const loadConversations = async (selectLatest = false) => {
    try {
      const data = await api.getConversations();
      setConversations(data);
      if (selectLatest && data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  useEffect(() => {
    loadConversations(true);
  }, []);

  useEffect(() => {
    if (initialSessionId) {
      setActiveSessionId(initialSessionId);
    }
  }, [initialSessionId]);

  // Load active conversation messages
  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      return;
    }
    const fetchConversation = async () => {
      try {
        setLoading(true);
        setErrorMsg(null);
        const conv = await api.getConversation(activeSessionId);
        setMessages(conv.messages || []);
        if (conv.customer_id) setCustomerId(conv.customer_id);
      } catch (err: any) {
        setErrorMsg(err.message || 'Could not fetch conversation history');
      } finally {
        setLoading(false);
      }
    };
    fetchConversation();
  }, [activeSessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleNewChat = () => {
    const newSessionId = `sess-${Date.now()}`;
    setActiveSessionId(newSessionId);
    setMessages([]);
    setSelectedFile(null);
    setUploadedFileInfo(null);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setUploading(true);
      setSelectedFile(file);
      const info = await api.uploadFile(file);
      setUploadedFileInfo(info);
    } catch (err: any) {
      setErrorMsg(`Failed to upload/parse file: ${err.message}`);
      setSelectedFile(null);
    } finally {
      setUploading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() && !uploadedFileInfo) return;

    const userText = inputText.trim();
    setInputText('');
    setErrorMsg(null);

    const tempUserMsg: ChatMessage = {
      id: `tmp-${Date.now()}`,
      session_id: activeSessionId,
      sender: 'customer',
      content: userText || `[Attached File: ${uploadedFileInfo?.original_filename}]`,
      timestamp: new Date().toISOString(),
      file_info: uploadedFileInfo,
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsTyping(true);

    try {
      const response = await api.sendMessage({
        customer_id: customerId,
        message: userText,
        session_id: activeSessionId,
        reference_date: referenceDate || undefined,
        user_access_level: accessLevel,
        uploaded_file: uploadedFileInfo?.storage_path,
      });

      if (!activeSessionId || activeSessionId.startsWith('sess-')) {
        setActiveSessionId(response.session_id);
      }

      const botMsg: ChatMessage = {
        id: `bot-${Date.now()}`,
        session_id: response.session_id,
        sender: 'sentinel',
        content: response.reply,
        timestamp: response.timestamp || new Date().toISOString(),
        sentiment: response.sentiment,
        confidence: response.confidence,
        is_high_risk: response.is_high_risk,
        risk_category: response.risk_category,
        risk_level: response.risk_level,
        escalated: response.escalated,
        escalation_reason: response.escalation_reason,
        ticket_id: response.ticket_id,
        assigned_team: response.assigned_team,
        sources: response.sources,
        file_info: response.file_result,
      };

      setMessages((prev) => {
        const updated = [...prev];
        let lastUserIdx = -1;
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].sender === 'customer') {
            lastUserIdx = i;
            break;
          }
        }
        if (lastUserIdx !== -1) {
          updated[lastUserIdx] = {
            ...updated[lastUserIdx],
            sentiment: response.sentiment,
            confidence: response.confidence,
            is_high_risk: response.is_high_risk,
            risk_category: response.risk_category,
            risk_level: response.risk_level,
            escalated: response.escalated,
            escalation_reason: response.escalation_reason,
          };
        }
        return [...updated, botMsg];
      });
      setSelectedFile(null);
      setUploadedFileInfo(null);

      loadConversations();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to send message to Sentinel');
    } finally {
      setIsTyping(false);
    }
  };

  const activeConv = conversations.find((c) => c.id === activeSessionId);
  const latestCustomerMessage = [...messages].reverse().find((m) => m.sender === 'customer');
  const latestBotMessage = [...messages].reverse().find((m) => m.sender === 'sentinel');
  const activeTicketId = latestBotMessage?.ticket_id || activeConv?.ticket_id;
  const activeTeam = latestBotMessage?.assigned_team || activeConv?.assigned_team;
  const activeRiskCategory = latestCustomerMessage?.risk_category || latestBotMessage?.risk_category || activeConv?.risk_category;
  const activeRiskLevel = latestCustomerMessage?.risk_level || latestBotMessage?.risk_level || activeConv?.risk_level || (activeConv?.is_high_risk ? 'critical' : 'none');
  const activeSources = latestBotMessage?.sources || [];

  const quickPrompts = [
    'What is the warranty policy for the UltraLaptop?',
    'What was the warranty coverage for purchases made in March 2024?',
    'I noticed an unauthorized access on my account and double charged payment.',
    'Oh great, another delayed package. Wonderful customer service as always!',
    'Here is my invoice, I was charged $150.00 for order ORD-998811.',
    'Where is my order? It was supposed to arrive yesterday.',
  ];

  const filteredConversations = conversations.filter(
    (c) =>
      c.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.customer_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* ── Left Sidebar: Conversation List ── */}
      <div className="w-72 border-r border-border bg-card flex flex-col shrink-0">
        <div className="p-3 border-b border-border space-y-2">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-md bg-zinc-100 text-zinc-950 font-medium text-xs hover:bg-white transition-colors shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Customer Session</span>
          </button>
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Filter sessions..."
              className="w-full pl-7 pr-2.5 py-1 rounded bg-zinc-900 border border-border text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-500"
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto divide-y divide-border/60 p-2 space-y-0.5">
          {filteredConversations.map((c) => {
            const isActive = c.id === activeSessionId;
            return (
              <div
                key={c.id}
                onClick={() => setActiveSessionId(c.id)}
                className={`p-2.5 rounded-md cursor-pointer transition-colors space-y-1 ${
                  isActive
                    ? 'bg-zinc-800/90 text-zinc-100 border border-white/[0.06] shadow-sm'
                    : 'hover:bg-zinc-900/60 text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <div className="flex items-center justify-between gap-1">
                  <span className="text-xs font-medium text-zinc-200 truncate">
                    {c.title}
                  </span>
                  <span className="text-[10px] font-mono text-zinc-500 shrink-0">
                    {new Date(c.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-zinc-500 truncate max-w-[130px]">{c.customer_name || c.customer_id}</span>
                  <div className="flex items-center gap-1.5">
                    {c.is_high_risk && (
                      <span className="text-[9px] font-mono font-medium text-red-400 bg-red-500/10 border border-red-500/20 px-1 rounded">
                        RISK
                      </span>
                    )}
                    <SentimentBadge sentiment={c.last_sentiment} size="sm" />
                  </div>
                </div>
              </div>
            );
          })}
          {filteredConversations.length === 0 && (
            <div className="p-6 text-center text-xs text-zinc-500 font-mono">
              No matching sessions found.
            </div>
          )}
        </div>

        {/* User Context Controls */}
        <div className="p-3 border-t border-border bg-zinc-950/40 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-zinc-400 text-[11px]">Customer ID:</span>
            <input
              type="text"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              className="w-28 px-2 py-0.5 rounded bg-zinc-900 border border-border text-zinc-200 font-mono text-[11px] text-right focus:outline-none focus:border-zinc-500"
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-zinc-400 text-[11px]">RBAC Tier:</span>
            <select
              value={accessLevel}
              onChange={(e) => setAccessLevel(e.target.value)}
              className="px-2 py-0.5 rounded bg-zinc-900 border border-border text-zinc-200 text-[11px] focus:outline-none focus:border-zinc-500"
            >
              <option value="public">Public</option>
              <option value="internal">Internal</option>
              <option value="restricted">Restricted</option>
              <option value="confidential">Confidential</option>
            </select>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-zinc-400 text-[11px]">Ref Date (RAG):</span>
            <input
              type="date"
              value={referenceDate}
              onChange={(e) => setReferenceDate(e.target.value)}
              className="px-1.5 py-0.5 rounded bg-zinc-900 border border-border text-zinc-200 text-[11px] focus:outline-none focus:border-zinc-500"
            />
          </div>
        </div>
      </div>

      {/* ── Center: Main Chat Messages Flow ── */}
      <div className="flex-1 flex flex-col justify-between bg-background overflow-hidden">
        {/* Session Sub-header */}
        <div className="px-5 py-2.5 border-b border-border bg-card/40 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-md bg-zinc-800 border border-zinc-700/60 flex items-center justify-center text-zinc-300">
              <Shield className="w-3.5 h-3.5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-zinc-200">
                  {activeConv?.title || 'Interactive Support Session'}
                </span>
                <span className="text-[10px] text-zinc-500 font-mono">
                  ({activeSessionId.slice(0, 12)}...)
                </span>
              </div>
              <div className="text-[11px] text-zinc-500 flex items-center gap-2">
                <span>Customer: <strong className="text-zinc-300 font-medium">{customerId}</strong></span>
                <span>•</span>
                <span>RBAC: <span className="capitalize text-zinc-300 font-medium">{accessLevel}</span></span>
                {referenceDate && (
                  <>
                    <span>•</span>
                    <span className="text-amber-400 font-mono text-[10px]">Date Anchor: {referenceDate}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={() => setShowInspector(!showInspector)}
            className="flex items-center gap-1.5 text-[11px] text-zinc-400 hover:text-zinc-200 px-2.5 py-1 rounded border border-border bg-zinc-900/40 hover:bg-zinc-800 transition-colors"
          >
            <Info className="w-3.5 h-3.5" />
            <span>{showInspector ? 'Hide Inspector' : 'Show Inspector'}</span>
          </button>
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && !loading && (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4 max-w-lg mx-auto">
              <div className="w-10 h-10 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-300 shadow-sm">
                <Shield className="w-5 h-5 text-zinc-300" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-zinc-200">Sentinel Chatbot Engine Online</h3>
                <p className="text-xs text-zinc-500">
                  Test sentiment classification, context-aware sarcasm detection, high-risk security escalation,
                  intent-grounded RAG retrieval, and receipt discrepancy verification.
                </p>
              </div>

              {/* Quick Prompts */}
              <div className="w-full text-left space-y-1.5 pt-2">
                <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block">
                  Interactive Evaluation Probes:
                </span>
                <div className="grid grid-cols-1 gap-1.5">
                  {quickPrompts.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setInputText(prompt);
                        if (prompt.includes('March 2024')) {
                          setReferenceDate('2024-03-15');
                        }
                      }}
                      className="text-xs text-left p-2.5 rounded-md bg-zinc-900/60 border border-border hover:border-zinc-700 text-zinc-300 hover:text-white transition-colors flex items-center justify-between group"
                    >
                      <span className="truncate">{prompt}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-300 shrink-0 ml-2" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {messages.map((m) => {
            const isBot = m.sender === 'sentinel';
            return (
              <div
                key={m.id}
                className={`flex gap-3 max-w-2xl ${isBot ? 'mr-auto' : 'ml-auto flex-row-reverse'}`}
              >
                {/* Avatar */}
                <div
                  className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 border text-[11px] font-mono ${
                    isBot
                      ? 'bg-zinc-800 text-zinc-300 border-zinc-700'
                      : 'bg-zinc-900 text-zinc-300 border-zinc-700'
                  }`}
                >
                  {isBot ? <Shield className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
                </div>

                {/* Content Bubble */}
                <div className="space-y-1">
                  <div
                    className={`p-3.5 rounded-lg text-xs leading-relaxed ${
                      isBot
                        ? 'bg-card border border-border text-zinc-200 shadow-sm'
                        : 'bg-zinc-800/90 text-zinc-100 border border-zinc-700/80 shadow-sm'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{m.content}</div>

                    {/* File Attachment Badge */}
                    {m.file_info && (
                      <div className="mt-3 p-2.5 rounded bg-zinc-950/70 border border-border text-zinc-300 space-y-1 text-[11px]">
                        <div className="flex items-center gap-1.5 font-medium text-zinc-200">
                          <FileText className="w-3.5 h-3.5 text-zinc-400" />
                          <span>Processed Attachment: {m.file_info.file_type?.toUpperCase()}</span>
                        </div>
                        {m.file_info.extracted_order_ids?.length > 0 && (
                          <div className="text-zinc-400">
                            Order IDs: <span className="font-mono text-zinc-200">{m.file_info.extracted_order_ids.join(', ')}</span>
                          </div>
                        )}
                        {m.file_info.extracted_amounts?.length > 0 && (
                          <div className="text-zinc-400">
                            Amounts: <span className="font-mono text-zinc-200">{m.file_info.extracted_amounts.join(', ')}</span>
                          </div>
                        )}
                        {m.file_info.conflicts_detected?.length > 0 && (
                          <div className="text-amber-400 font-medium">
                            Discrepancies: {m.file_info.conflicts_detected.join(' | ')}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Grounding Sources & Citations */}
                    {isBot && m.sources && m.sources.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-border/60 text-[11px] space-y-1.5">
                        <span className="font-semibold text-zinc-400 block text-[10px] uppercase tracking-wider">
                          Grounding Evidence:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {m.sources.map((src, i) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 rounded bg-zinc-900 border border-border text-zinc-300 flex items-center gap-1 font-mono text-[10px]"
                            >
                              <ExternalLink className="w-2.5 h-2.5 text-zinc-500" />
                              {typeof src === 'string' ? src : src.title || src.document_id}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Metadata line */}
                  <div
                    className={`flex items-center gap-2 text-[10px] text-zinc-500 ${
                      isBot ? 'justify-start' : 'justify-end'
                    }`}
                  >
                    <span className="font-mono">
                      {new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {!isBot && m.sentiment && (
                      <div className="flex items-center gap-1.5">
                        <SentimentBadge sentiment={m.sentiment} confidence={m.confidence} isHighRisk={m.is_high_risk} size="sm" />
                      </div>
                    )}
                    {isBot && m.ticket_id && (
                      <span className="px-1.5 py-0.5 rounded bg-zinc-900 border border-border text-zinc-400 font-mono text-[10px] flex items-center gap-1">
                        <TicketIcon className="w-3 h-3 text-zinc-500" />
                        #{m.ticket_id.slice(0, 8)} • Team: {m.assigned_team?.toUpperCase() || 'GENERAL'}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {isTyping && (
            <div className="flex items-center gap-3 mr-auto">
              <div className="w-7 h-7 rounded-md bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-300">
                <Shield className="w-3.5 h-3.5" />
              </div>
              <div className="p-3 rounded-lg bg-card border border-border flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:-0.3s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:-0.15s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce" />
                <span className="text-[11px] text-zinc-500 font-mono ml-2">Reasoning & safety verification...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div className="mx-6 mb-2 p-3 rounded-md bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button onClick={() => setErrorMsg(null)} className="text-xs underline font-medium">
              Dismiss
            </button>
          </div>
        )}

        {/* Attachment Preview Banner */}
        {selectedFile && (
          <div className="mx-6 mb-2 p-2.5 rounded-md bg-zinc-900 border border-border flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-zinc-400" />
              <span className="font-medium text-zinc-200">{selectedFile.name}</span>
              <span className="text-zinc-500 font-mono">({(selectedFile.size / 1024).toFixed(1)} KB)</span>
              {uploading && <span className="text-zinc-300 font-mono text-[11px] animate-pulse">• Uploading & OCR validating...</span>}
              {uploadedFileInfo && <span className="text-emerald-400 font-mono text-[11px]">• OCR Validated</span>}
            </div>
            <button
              onClick={() => {
                setSelectedFile(null);
                setUploadedFileInfo(null);
              }}
              className="text-zinc-400 hover:text-zinc-200 text-xs"
            >
              Remove
            </button>
          </div>
        )}

        {/* Input Bar Form */}
        <form onSubmit={handleSendMessage} className="p-3.5 border-t border-border bg-card">
          <div className="flex items-center gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              className="hidden"
              accept=".txt,.pdf,.png,.jpg,.jpeg,.csv,.json"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-2 rounded border border-border text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
              title="Upload invoice, screenshot or document"
            >
              <Paperclip className="w-4 h-4" />
            </button>

            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Type customer inquiry or policy question..."
              className="flex-1 px-3 py-2 rounded bg-zinc-900 border border-border text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-500 transition-colors"
            />

            <button
              type="submit"
              disabled={(!inputText.trim() && !uploadedFileInfo) || isTyping}
              className="px-3.5 py-2 rounded bg-zinc-100 text-zinc-950 text-xs font-medium hover:bg-white transition-colors disabled:opacity-40 flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Send</span>
            </button>
          </div>
        </form>
      </div>

      {/* ── Right Drawer: Live Conversation Intelligence Inspector ── */}
      {showInspector && (
        <div className="w-80 border-l border-border bg-card flex flex-col shrink-0 overflow-y-auto p-4 space-y-4">
          <div className="border-b border-border pb-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Operational Telemetry
            </h3>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              Live extracted signals across Sentinel subsystems
            </p>
          </div>

          {/* Customer Sentiment */}
          <div className="p-3.5 rounded-md bg-zinc-900/60 border border-border space-y-2">
            <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
              Sentiment Classification
            </span>
            <div className="flex items-center justify-between">
              <SentimentBadge
                sentiment={latestCustomerMessage?.sentiment || activeConv?.last_sentiment || 'neutral'}
                confidence={latestCustomerMessage?.confidence ?? activeConv?.last_confidence ?? 1.0}
              />
            </div>
          </div>

          {/* Risk Classification & Level */}
          <div className="p-3.5 rounded-md bg-zinc-900/60 border border-border space-y-2">
            <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
              Risk & Safety Status
            </span>
            <div className="space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Risk Assessment:</span>
                <span className={`font-mono text-[11px] font-semibold ${activeConv?.is_high_risk ? 'text-red-400' : 'text-emerald-400'}`}>
                  {activeConv?.is_high_risk ? 'HIGH RISK' : 'CLEAR'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Severity Level:</span>
                <span className={`font-mono text-[11px] uppercase ${
                  activeRiskLevel === 'critical' ? 'text-red-400 font-semibold' :
                  activeRiskLevel === 'high' ? 'text-amber-400' : 'text-zinc-500'
                }`}>
                  {activeRiskLevel.toUpperCase()}
                </span>
              </div>
              {activeRiskCategory && (
                <div className="flex items-center justify-between pt-1 border-t border-border">
                  <span className="text-zinc-400">Category:</span>
                  <span className="font-mono text-[11px] text-zinc-200 capitalize">
                    {activeRiskCategory.replace('_', ' ')}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Escalation & Ticket Routing */}
          <div className="p-3.5 rounded-md bg-zinc-900/60 border border-border space-y-2">
            <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
              Dispatch & SLA Routing
            </span>
            <div className="space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Escalated:</span>
                <span className={`font-mono text-[11px] ${activeConv?.escalated ? 'text-amber-400 font-semibold' : 'text-zinc-500'}`}>
                  {activeConv?.escalated ? 'YES' : 'NO'}
                </span>
              </div>
              {activeConv?.escalation_reason && (
                <div className="pt-1 border-t border-border">
                  <span className="text-zinc-500 text-[10px] block">Trigger Reason:</span>
                  <span className="font-mono text-[11px] text-zinc-300">
                    {activeConv.escalation_reason}
                  </span>
                </div>
              )}
              {activeTicketId && (
                <div className="pt-2 border-t border-border space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-400">Ticket ID:</span>
                    <span className="font-mono text-[11px] text-zinc-200 font-semibold">
                      #{activeTicketId.slice(0, 8)}
                    </span>
                  </div>
                  {activeTeam && (
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-400">Assigned Team:</span>
                      <span className="font-medium text-zinc-200 uppercase text-[11px]">
                        {activeTeam.replace('_', ' ')}
                      </span>
                    </div>
                  )}
                  <button
                    onClick={() => onNavigateToTicket && onNavigateToTicket(activeTicketId)}
                    className="w-full mt-1.5 flex items-center justify-center gap-1.5 py-1.5 rounded bg-zinc-100 text-zinc-950 text-xs font-medium hover:bg-white transition-colors"
                  >
                    <TicketIcon className="w-3.5 h-3.5" />
                    <span>View in Ticket Queue</span>
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Grounding Knowledge Sources */}
          {activeSources.length > 0 && (
            <div className="p-3.5 rounded-md bg-zinc-900/60 border border-border space-y-2 text-xs">
              <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                Grounded Knowledge Sources
              </span>
              <div className="space-y-1.5">
                {activeSources.map((src, i) => (
                  <div key={i} className="p-2 rounded bg-zinc-950 border border-border text-[11px] space-y-0.5">
                    <div className="font-medium text-zinc-200 flex items-center gap-1">
                      <ExternalLink className="w-3 h-3 text-zinc-500 shrink-0" />
                      <span>{src.title || src.document_id}</span>
                    </div>
                    {src.version && (
                      <div className="text-[10px] font-mono text-zinc-500">
                        v{src.version} • {src.access_level?.toUpperCase()}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Customer Metadata */}
          <div className="p-3.5 rounded-md bg-zinc-900/60 border border-border space-y-2 text-xs">
            <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">Session Metadata</span>
            <div className="space-y-1 text-zinc-400 text-[11px]">
              <div className="flex justify-between">
                <span>Customer ID:</span>
                <span className="font-mono text-zinc-200">{customerId}</span>
              </div>
              <div className="flex justify-between">
                <span>Detected Lang:</span>
                <span className="font-mono text-zinc-200 uppercase">
                  {latestCustomerMessage?.language || 'en'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Access Level:</span>
                <span className="capitalize text-zinc-200">{accessLevel}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
