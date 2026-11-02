import {
  AdminSettings,
  AnalyticsOverview,
  AnalyticsTrends,
  Conversation,
  KnowledgeDocument,
  Ticket,
} from '../types';

const API_BASE = '/api';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) errorMsg = errJson.detail;
      else if (errJson.error) errorMsg = errJson.error;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export const api = {
  // Chat
  async sendMessage(params: {
    customer_id: string;
    message: string;
    session_id?: string;
    reference_date?: string;
    user_access_level?: string;
    uploaded_file?: string;
  }) {
    return request<any>('/chat/message', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async uploadFile(file: File, customerId: string = 'cust-101', sessionId?: string) {
    const formData = new FormData();
    formData.append('file', file);
    const query = new URLSearchParams({ customer_id: customerId });
    if (sessionId) query.append('session_id', sessionId);

    const response = await fetch(`${API_BASE}/chat/upload?${query.toString()}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return response.json();
  },

  async getConversations(status?: string, search?: string) {
    const q = new URLSearchParams();
    if (status && status !== 'all') q.append('status', status);
    if (search) q.append('search', search);
    return request<Conversation[]>(`/chat/conversations?${q.toString()}`);
  },

  async getConversation(sessionId: string) {
    return request<Conversation>(`/chat/conversations/${sessionId}`);
  },

  async deleteConversation(sessionId: string) {
    return request<any>(`/chat/conversations/${sessionId}`, { method: 'DELETE' });
  },

  // Tickets
  async getTickets(filters: { status?: string; priority?: string; team?: string; search?: string } = {}) {
    const q = new URLSearchParams();
    if (filters.status && filters.status !== 'all') q.append('status', filters.status);
    if (filters.priority && filters.priority !== 'all') q.append('priority', filters.priority);
    if (filters.team && filters.team !== 'all') q.append('team', filters.team);
    if (filters.search) q.append('search', filters.search);
    return request<Ticket[]>(`/tickets?${q.toString()}`);
  },

  async getTicket(ticketId: string) {
    return request<Ticket>(`/tickets/${ticketId}`);
  },

  async updateTicket(ticketId: string, updates: Partial<Ticket>) {
    return request<Ticket>(`/tickets/${ticketId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  async addTicketNote(ticketId: string, author: string, content: string) {
    return request<any>(`/tickets/${ticketId}/notes`, {
      method: 'POST',
      body: JSON.stringify({ author, content }),
    });
  },

  // Knowledge Base
  async getDocuments(accessLevel?: string, status?: string, search?: string) {
    const q = new URLSearchParams();
    if (accessLevel && accessLevel !== 'all') q.append('access_level', accessLevel);
    if (status && status !== 'all') q.append('status', status);
    if (search) q.append('search', search);
    return request<KnowledgeDocument[]>(`/knowledge/documents?${q.toString()}`);
  },

  async createDocument(doc: {
    title: string;
    content: string;
    product?: string;
    region?: string;
    access_level?: string;
    version?: number;
    effective_date?: string;
    expiry_date?: string;
  }) {
    return request<KnowledgeDocument>('/knowledge/documents', {
      method: 'POST',
      body: JSON.stringify(doc),
    });
  },

  async syncKnowledge() {
    return request<{ status: string; total_documents: number }>('/knowledge/sync', {
      method: 'POST',
    });
  },

  // Analytics
  async getAnalyticsOverview() {
    return request<AnalyticsOverview>('/analytics/overview');
  },

  async getAnalyticsTrends() {
    return request<AnalyticsTrends>('/analytics/trends');
  },

  // Admin Settings
  async getAdminSettings() {
    return request<AdminSettings>('/admin/settings');
  },

  async updateAdminSettings(updates: Partial<AdminSettings>) {
    return request<AdminSettings>('/admin/settings', {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  // Health
  async getHealth() {
    return request<any>('/health');
  },
};

