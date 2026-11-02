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

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleNewChat = () => {
    const newId = `sess-${Date.now().toString(36)}`;
    setActiveSessionId(newId);
    setMessages([]);
    setInputText('');
    setUploadedFileInfo(null);
    setSelectedFile(null);
    setErrorMsg(null);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSelectedFile(file);
    setUploading(true);
    setErrorMsg(null);

    try {
      const res = await api.uploadFile(file, customerId, activeSessionId);
      setUploadedFileInfo(res);
      if (!res.is_safe) {
        setErrorMsg('The uploaded file was rejected due to safety or prompt-injection policy.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'File upload failed');
      setSelectedFile(null);
    } finally {
      setUploading(false);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() && !uploadedFileInfo) return;

    const textToSend = inputText.trim();
    setInputText('');
    setErrorMsg(null);

    // Optimistically append user message
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      session_id: activeSessionId || 'pending',
      sender: 'customer',
      content: textToSend || `Uploaded file: ${selectedFile?.name}`,
      timestamp: new Date().toISOString(),
      language: 'en',
      is_high_risk: false,
      escalated: false,
      file_info: uploadedFileInfo,
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsTyping(true);

    try {
      const response = await api.sendMessage({
        customer_id: customerId,
        message: textToSend || `Please analyze this attached document: ${selectedFile?.name}`,
        session_id: activeSessionId || undefined,
        reference_date: referenceDate || undefined,
        user_access_level: accessLevel,
        uploaded_file: uploadedFileInfo?.file_path,
      });

      // Update active session ID if newly assigned
      if (response.session_id && response.session_id !== activeSessionId) {
        setActiveSessionId(response.session_id);
      }

      // Append bot response
      const botMsg: ChatMessage = {
        id: Date.now() + 1,
        session_id: response.session_id,
        sender: 'sentinel',
        content: response.reply,
        timestamp: response.timestamp || new Date().toISOString(),
        language: 'en',
        sentiment: response.sentiment,
        confidence: response.confidence,
        is_high_risk: response.is_high_risk,
        escalated: response.escalated,
        escalation_reason: response.escalation_reason,
        sources: response.sources || [],
      };

      setMessages((prev) => [...prev, botMsg]);
      setSelectedFile(null);
      setUploadedFileInfo(null);

      // Refresh conversation list in sidebar
      loadConversations();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to send message to Sentinel');
    } finally {
      setIsTyping(false);
    }
  };

  const activeConv = conversations.find((c) => c.id === activeSessionId);
  const latestMessage = messages.length > 0 ? messages[messages.length - 1] : null;

  const quickPrompts = [
    'What is the warranty policy for the UltraLaptop?',
    'What was the warranty coverage for purchases made in March 2024?',
    'I noticed an unauthorized access on my account and double charged payment.',
    'Oh great, another delayed package. Wonderful customer service as always!',
    'Here is my invoice, I was charged $150.00 for order ORD-998811.',
    'Mera order kab deliver hoga mujhe status update chahiye.',
  ];

  const filteredConversations = conversations.filter(
    (c) =>
      c.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.customer_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
      {/* ── Left Sidebar: Conversation History ── */}
      <div className="w-80 border-r border-border bg-card/60 flex flex-col shrink-0">
        <div className="p-3 border-b border-border space-y-2">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-primary text-primary-foreground font-medium text-xs shadow-sm hover:opacity-95 transition-opacity"
          >
            <Plus className="w-4 h-4" />
            <span>New Customer Chat</span>
          </button>
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search conversations..."
              className="w-full pl-8 pr-3 py-1.5 rounded-md bg-muted/50 border border-border text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto divide-y divide-border/40 p-2 space-y-0.5">
          {filteredConversations.map((c) => {
            const isActive = c.id === activeSessionId;
            return (
              <div
                key={c.id}
                onClick={() => setActiveSessionId(c.id)}
                className={`p-3 rounded-lg cursor-pointer transition-all space-y-1.5 ${
                  isActive
                    ? 'bg-primary/10 border border-primary/20 text-foreground'
                    : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-foreground truncate max-w-[170px]">
                    {c.title}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {new Date(c.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-muted-foreground truncate">{c.customer_name || c.customer_id}</span>
                  <div className="flex items-center gap-1.5">
                    {c.is_high_risk && (
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" />
                    )}
                    <SentimentBadge sentiment={c.last_sentiment} size="sm" />
                  </div>
                </div>
              </div>
            );
          })}
          {filteredConversations.length === 0 && (
            <div className="p-6 text-center text-xs text-muted-foreground">
              No matching conversations.
            </div>
          )}
        </div>

        {/* User Context Controls */}
        <div className="p-3 border-t border-border bg-card/80 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground font-medium">Customer ID:</span>
            <input
              type="text"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              className="w-28 px-2 py-0.5 rounded bg-muted/60 border border-border text-foreground font-mono text-[11px] text-right"
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground font-medium">RBAC Tier:</span>
            <select
              value={accessLevel}
              onChange={(e) => setAccessLevel(e.target.value)}
              className="px-2 py-0.5 rounded bg-muted/60 border border-border text-foreground text-[11px]"
            >
              <option value="public">Public</option>
              <option value="internal">Internal</option>
              <option value="restricted">Restricted</option>
              <option value="confidential">Confidential</option>
            </select>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground font-medium">Ref Date (RAG):</span>
            <input
              type="date"
              value={referenceDate}
              onChange={(e) => setReferenceDate(e.target.value)}
              className="px-1.5 py-0.5 rounded bg-muted/60 border border-border text-foreground text-[11px]"
            />
          </div>
        </div>
      </div>

      {/* ── Center: Main Chat Messages Flow ── */}
      <div className="flex-1 flex flex-col justify-between bg-background overflow-hidden">
        {/* Session Sub-header */}
        <div className="px-6 py-2.5 border-b border-border bg-card/40 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-foreground">
                  {activeConv?.title || 'Interactive Support Session'}
                </span>
                <span className="text-[10px] text-muted-foreground font-mono">
                  ({activeSessionId.slice(0, 14)}...)
                </span>
              </div>
              <div className="text-[11px] text-muted-foreground flex items-center gap-2">
                <span>Customer: <strong className="text-foreground font-medium">{customerId}</strong></span>
                <span>•</span>
                <span>RBAC: <span className="capitalize text-primary font-medium">{accessLevel}</span></span>
                {referenceDate && (
                  <>
                    <span>•</span>
                    <span className="text-amber-500 font-medium">Historical Query: {referenceDate}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={() => setShowInspector(!showInspector)}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground px-2.5 py-1 rounded-md border border-border bg-muted/40 hover:bg-muted"
          >
            <Info className="w-3.5 h-3.5" />
            <span>{showInspector ? 'Hide Inspector' : 'Show Inspector'}</span>
          </button>
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && !loading && (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4 max-w-lg mx-auto">
              <div className="w-12 h-12 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shadow-sm">
                <Shield className="w-6 h-6 text-primary" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-foreground">Sentinel Chatbot Engine Ready</h3>
                <p className="text-xs text-muted-foreground">
                  Test live multilingual sentiment analysis, sarcasm detection, calm high-risk escalations,
                  temporal RAG policies, or upload an invoice for multimodal OCR validation.
                </p>
              </div>

              {/* Quick Prompts */}
              <div className="w-full text-left space-y-1.5 pt-2">
                <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                  Quick Evaluation Prompts:
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
                      className="text-xs text-left p-2 rounded-lg bg-card border border-border hover:border-primary/40 text-foreground transition-all flex items-center justify-between group"
                    >
                      <span className="truncate">{prompt}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary shrink-0 ml-2" />
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
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border text-xs font-semibold ${
                    isBot
                      ? 'bg-primary/10 text-primary border-primary/20'
                      : 'bg-muted text-foreground border-border'
                  }`}
                >
                  {isBot ? <Shield className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>

                {/* Content Bubble */}
                <div className="space-y-1.5">
                  <div
                    className={`p-4 rounded-2xl text-xs leading-relaxed ${
                      isBot
                        ? 'bg-card border border-border text-foreground shadow-sm'
                        : 'bg-primary text-primary-foreground shadow-sm'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{m.content}</div>

                    {/* File Attachment Badge */}
                    {m.file_info && (
                      <div className="mt-3 p-2.5 rounded-lg bg-background/80 border border-border text-foreground space-y-1 text-[11px]">
                        <div className="flex items-center gap-1.5 font-semibold text-primary">
                          <FileText className="w-3.5 h-3.5" />
                          <span>Processed File: {m.file_info.file_type?.toUpperCase()}</span>
                        </div>
                        {m.file_info.extracted_order_ids?.length > 0 && (
                          <div>Order IDs: <span className="font-mono">{m.file_info.extracted_order_ids.join(', ')}</span></div>
                        )}
                        {m.file_info.extracted_amounts?.length > 0 && (
                          <div>Amounts: <span className="font-mono">{m.file_info.extracted_amounts.join(', ')}</span></div>
                        )}
                        {m.file_info.conflicts_detected?.length > 0 && (
                          <div className="text-amber-500 font-medium">
                            Discrepancies: {m.file_info.conflicts_detected.join(' | ')}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Grounding Sources & Citations */}
                    {isBot && m.sources && m.sources.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-border/60 text-[11px] space-y-1">
                        <span className="font-semibold text-muted-foreground block">Verified Knowledge Sources:</span>
                        <div className="flex flex-wrap gap-1.5">
                          {m.sources.map((src, i) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 rounded bg-muted/60 border border-border text-foreground flex items-center gap-1"
                            >
                              <ExternalLink className="w-2.5 h-2.5 text-primary" />
                              {typeof src === 'string' ? src : src.title || src.document_id}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Metadata line */}
                  <div
                    className={`flex items-center gap-2 text-[10px] text-muted-foreground ${
                      isBot ? 'justify-start' : 'justify-end'
                    }`}
                  >
                    <span>{new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    {isBot && m.sentiment && (
                      <SentimentBadge sentiment={m.sentiment} confidence={m.confidence} isHighRisk={m.is_high_risk} size="sm" />
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {isTyping && (
            <div className="flex items-center gap-3 mr-auto">
              <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                <Shield className="w-4 h-4" />
              </div>
              <div className="p-3.5 rounded-2xl bg-card border border-border flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" />
                <span className="text-xs text-muted-foreground ml-2 font-medium">Sentinel reasoning & safety checking...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div className="mx-6 mb-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-center justify-between">
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
          <div className="mx-6 mb-2 p-2.5 rounded-lg bg-card border border-border flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-primary" />
              <span className="font-medium text-foreground">{selectedFile.name}</span>
              <span className="text-muted-foreground">({(selectedFile.size / 1024).toFixed(1)} KB)</span>
              {uploading && <span className="text-primary font-semibold animate-pulse">• Uploading & OCR validating...</span>}
              {uploadedFileInfo && <span className="text-emerald-500 font-semibold">• OCR Validated</span>}
            </div>
            <button
              onClick={() => {
                setSelectedFile(null);
                setUploadedFileInfo(null);
              }}
              className="text-muted-foreground hover:text-foreground text-xs"
            >
              Remove
            </button>
          </div>
        )}

        {/* Input Bar Form */}
        <form onSubmit={handleSendMessage} className="p-4 border-t border-border bg-card">
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
              className="p-2.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
              title="Upload invoice, screenshot or document"
            >
              <Paperclip className="w-4 h-4" />
            </button>

            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask a question, enter an order ID, or report an issue..."
              className="flex-1 px-4 py-2.5 rounded-lg bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground/70"
            />

            <button
              type="submit"
              disabled={(!inputText.trim() && !uploadedFileInfo) || isTyping}
              className="px-4 py-2.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold shadow-sm hover:opacity-95 transition-opacity disabled:opacity-50 flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Send</span>
            </button>
          </div>
        </form>
      </div>

      {/* ── Right Drawer: Live Conversation Intelligence Inspector ── */}
      {showInspector && (
        <div className="w-80 border-l border-border bg-card/60 flex flex-col shrink-0 overflow-y-auto p-5 space-y-6">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Conversation Intelligence
            </h3>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Live telemetry extracted by Sentinel subsystems
            </p>
          </div>

          {/* Sentiment Status Card */}
          <div className="p-3.5 rounded-xl bg-card border border-border space-y-2.5">
            <span className="text-[11px] font-semibold text-muted-foreground block">
              Sentiment Classification
            </span>
            <div className="flex items-center justify-between">
              <SentimentBadge
                sentiment={latestMessage?.sentiment || activeConv?.last_sentiment || 'neutral'}
                confidence={latestMessage?.confidence ?? activeConv?.last_confidence ?? 1.0}
              />
            </div>
            <div className="text-[11px] text-muted-foreground">
              Confidence score: {Math.round((latestMessage?.confidence ?? activeConv?.last_confidence ?? 1.0) * 100)}%
            </div>
          </div>

          {/* Risk & Escalation Card */}
          <div className="p-3.5 rounded-xl bg-card border border-border space-y-2.5">
            <span className="text-[11px] font-semibold text-muted-foreground block">
              Risk & Escalation Status
            </span>
            <div className="space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">High Risk Incident:</span>
                <span className={`font-semibold ${activeConv?.is_high_risk ? 'text-rose-500' : 'text-emerald-500'}`}>
                  {activeConv?.is_high_risk ? 'YES (CRITICAL)' : 'NO (CLEAR)'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Escalation Triggered:</span>
                <span className={`font-semibold ${activeConv?.escalated ? 'text-orange-500' : 'text-slate-500'}`}>
                  {activeConv?.escalated ? 'TRUE' : 'FALSE'}
                </span>
              </div>
              {activeConv?.escalation_reason && (
                <div className="pt-1 border-t border-border/60">
                  <span className="text-muted-foreground block">Reason:</span>
                  <span className="font-mono text-[11px] text-foreground font-medium">
                    {activeConv.escalation_reason}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Associated Support Ticket if Escalated */}
          {activeConv?.escalated && (
            <div className="p-3.5 rounded-xl bg-primary/5 border border-primary/20 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-primary">Associated Ticket</span>
                <span className="text-[10px] font-mono text-muted-foreground">Automated</span>
              </div>
              <p className="text-xs text-foreground font-medium">
                Inquiry escalated to specialized support queue.
              </p>
              <button
                onClick={() => onNavigateToTicket && onNavigateToTicket('')}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-md bg-primary text-primary-foreground text-xs font-semibold shadow-sm hover:opacity-90"
              >
                <TicketIcon className="w-3.5 h-3.5" />
                <span>View Support Tickets</span>
              </button>
            </div>
          )}

          {/* Customer Metadata Card */}
          <div className="p-3.5 rounded-xl bg-card border border-border space-y-2 text-xs">
            <span className="text-[11px] font-semibold text-muted-foreground block">Customer Details</span>
            <div className="space-y-1 text-muted-foreground">
              <div className="flex justify-between">
                <span>Customer ID:</span>
                <span className="font-mono text-foreground font-medium">{customerId}</span>
              </div>
              <div className="flex justify-between">
                <span>Language:</span>
                <span className="text-foreground font-medium uppercase">
                  {latestMessage?.language || 'en'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Access Level:</span>
                <span className="text-foreground capitalize font-medium">{accessLevel}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

