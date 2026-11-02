export type SentimentType = 'positive' | 'neutral' | 'negative' | 'frustrated' | 'urgent' | 'sarcastic';

export type TicketPriority = 'low' | 'medium' | 'high' | 'critical';

export type TicketStatus = 'Open' | 'In Progress' | 'Pending' | 'Escalated' | 'Resolved' | 'Closed';

export type DocumentAccessLevel = 'public' | 'internal' | 'restricted' | 'confidential';

export interface FileInfo {
  file_path: string;
  file_type?: string;
  is_safe: boolean;
  status: string;
  extracted_order_ids?: string[];
  extracted_dates?: string[];
  extracted_amounts?: string[];
  extracted_error_codes?: string[];
  conflicts_detected?: string[];
  quality_score?: number;
}

export interface ChatMessage {
  id: number;
  session_id: string;
  sender: 'customer' | 'sentinel';
  content: string;
  timestamp: string;
  language: string;
  sentiment?: SentimentType;
  confidence?: number;
  is_high_risk: boolean;
  escalated: boolean;
  escalation_reason?: string;
  sources?: any[];
  file_info?: FileInfo | null;
}

export interface Conversation {
  id: string;
  customer_id: string;
  customer_name?: string;
  title: string;
  status: 'active' | 'escalated' | 'resolved' | 'closed';
  last_sentiment: SentimentType;
  last_confidence: number;
  is_high_risk: boolean;
  escalated: boolean;
  escalation_reason?: string;
  language: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
  messages?: ChatMessage[];
}

export interface InternalNote {
  id: number;
  ticket_id: string;
  author: string;
  content: string;
  created_at: string;
}

export interface Ticket {
  id: string;
  session_id?: string;
  customer_id: string;
  customer_name?: string;
  contact_email?: string;
  contact_phone?: string;
  order_id?: string;
  product_code?: string;
  issue_description: string;
  priority: TicketPriority;
  priority_score: number;
  status: TicketStatus;
  assigned_team: string;
  assigned_agent?: string;
  sla_deadline?: string;
  sla_hours?: number;
  sla_breached: boolean;
  escalation_reason?: string;
  handoff_summary?: string;
  duplicate_of?: string;
  created_at: string;
  updated_at: string;
  notes?: InternalNote[];
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  product: string;
  region: string;
  access_level: DocumentAccessLevel;
  version: number;
  effective_date: string;
  expiry_date?: string;
  content: string;
  status: 'active' | 'quarantined' | 'failed_quality' | 'archived';
  accuracy_score?: number;
  grounding_score?: number;
  quarantine_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface AnalyticsOverview {
  total_conversations: number;
  active_conversations: number;
  total_tickets: number;
  open_tickets: number;
  resolved_tickets: number;
  escalated_conversations: number;
  high_risk_incidents: number;
  average_response_time_ms: number;
}

export interface AnalyticsTrends {
  activity_timeline: Array<{ date: string; conversations: number; escalations: number }>;
  sentiment_counts: Record<string, number>;
  priority_counts: Record<string, number>;
  team_workload: Record<string, number>;
  language_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
}

export interface AdminSettings {
  app_name: string;
  version: string;
  business_hours_start: number;
  business_hours_end: number;
  sla_hours: Record<string, number>;
  escalation_negative_count: number;
  unresolved_escalation_minutes: number;
  session_timeout_minutes: number;
  supported_languages: string[];
  access_levels: string[];
  maintenance_window_start: number;
  maintenance_window_end: number;
}

