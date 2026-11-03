import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Plus,
  Search,
  ShieldCheck,
  ShieldAlert,
  RotateCw,
  X,
  FileText,
  Lock,
} from 'lucide-react';
import { api } from '../api/client';
import { DocumentAccessLevel, KnowledgeDocument } from '../types';

export const KnowledgePage: React.FC = () => {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [accessFilter, setAccessFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeDocument | null>(null);

  // Form state
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [product, setProduct] = useState('General');
  const [region, setRegion] = useState('global');
  const [accessLevel, setAccessLevel] = useState<DocumentAccessLevel>('public');
  const [version, setVersion] = useState(1);
  const [effectiveDate, setEffectiveDate] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [creationResult, setCreationResult] = useState<KnowledgeDocument | null>(null);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const data = await api.getDocuments(
        accessFilter !== 'all' ? accessFilter : undefined,
        statusFilter !== 'all' ? statusFilter : undefined,
        searchQuery || undefined
      );
      setDocuments(data);
    } catch (err) {
      console.error('Failed to load knowledge documents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [accessFilter, statusFilter, searchQuery]);

  const handleSyncKnowledge = async () => {
    try {
      await api.syncKnowledge();
      await loadDocuments();
    } catch (err) {
      console.error('Failed to sync knowledge:', err);
    }
  };

  const handleCreateDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return;

    try {
      setSubmitting(true);
      const res = await api.createDocument({
        title: title.trim(),
        content: content.trim(),
        product,
        region,
        access_level: accessLevel,
        version: Number(version),
        effective_date: effectiveDate || undefined,
        expiry_date: expiryDate || undefined,
      });

      setCreationResult(res);
      await loadDocuments();

      if (res.status === 'active') {
        setTimeout(() => {
          setShowAddModal(false);
          setCreationResult(null);
          setTitle('');
          setContent('');
        }, 1500);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to submit document');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100 tracking-tight">Knowledge Base & Policy Store</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Temporal policy resolution, automated quality gates, access tier gating, and quarantine security.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSyncKnowledge}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-900 border border-border hover:bg-zinc-800 text-xs font-medium text-zinc-300 transition-colors"
          >
            <RotateCw className="w-3.5 h-3.5 text-zinc-500" />
            <span>Sync Store</span>
          </button>
          <button
            onClick={() => {
              setCreationResult(null);
              setShowAddModal(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-100 text-zinc-950 hover:bg-white text-xs font-medium transition-colors shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Policy Document</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-3 rounded-lg border border-border bg-card grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search policies by keyword or product..."
            className="w-full pl-8 pr-3 py-1.5 rounded bg-zinc-900 border border-border text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-500 transition-colors"
          />
        </div>

        <div>
          <select
            value={accessFilter}
            onChange={(e) => setAccessFilter(e.target.value)}
            className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-xs text-zinc-200 focus:outline-none focus:border-zinc-500 transition-colors"
          >
            <option value="all">All Access Tiers</option>
            <option value="public">Public Access</option>
            <option value="internal">Internal Only</option>
            <option value="restricted">Restricted Tier</option>
            <option value="confidential">Confidential Tier</option>
          </select>
        </div>

        <div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-xs text-zinc-200 focus:outline-none focus:border-zinc-500 transition-colors"
          >
            <option value="all">All Pipeline Statuses</option>
            <option value="active">Active & Indexed</option>
            <option value="quarantined">Security Quarantined</option>
            <option value="failed_quality">Failed Quality Gate</option>
          </select>
        </div>
      </div>

      {/* Documents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {documents.map((doc) => {
          const isQuarantined = doc.status === 'quarantined';
          const isFailed = doc.status === 'failed_quality';

          return (
            <div
              key={doc.id}
              onClick={() => setSelectedDoc(doc)}
              className={`p-4 rounded-lg bg-card border transition-all cursor-pointer hover:border-zinc-700 flex flex-col justify-between space-y-3 ${
                isQuarantined
                  ? 'border-red-500/30 bg-red-500/5'
                  : isFailed
                  ? 'border-amber-500/30 bg-amber-500/5'
                  : 'border-border'
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-zinc-500">{doc.id}</span>
                  </div>

                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded border uppercase ${
                      doc.status === 'active'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : isQuarantined
                        ? 'bg-red-500/10 text-red-400 border-red-500/20'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}
                  >
                    {doc.status}
                  </span>
                </div>

                <h3 className="text-xs font-semibold text-zinc-200 leading-snug line-clamp-1">
                  {doc.title}
                </h3>

                <p className="text-[11px] text-zinc-500 line-clamp-2 leading-relaxed">
                  {doc.content}
                </p>
              </div>

              <div className="pt-2 border-t border-border flex items-center justify-between text-[11px] text-zinc-500">
                <div className="flex items-center gap-2 font-mono">
                  <span className="bg-zinc-800 px-1 py-0.5 rounded text-zinc-400 text-[10px]">
                    v{doc.version}
                  </span>
                  <span className="capitalize">{doc.access_level}</span>
                </div>
                <span className="font-mono text-[10px]">
                  {new Date(doc.effective_date).toLocaleDateString([], {
                    year: 'numeric',
                    month: 'short',
                  })}
                </span>
              </div>
            </div>
          );
        })}
        {documents.length === 0 && !loading && (
          <div className="col-span-3 py-12 text-center text-xs text-zinc-500 font-mono">
            No knowledge documents match the selected filters.
          </div>
        )}
      </div>

      {/* Add Document Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-card border border-border rounded-lg shadow-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-border flex items-center justify-between bg-zinc-900/50">
              <h3 className="text-xs font-semibold text-zinc-100 uppercase tracking-wider">
                Publish Document to Pipeline
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateDocument} className="p-5 space-y-4 text-xs">
              {creationResult && (
                <div
                  className={`p-3 rounded border text-xs flex items-center gap-2 ${
                    creationResult.status === 'active'
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                      : 'bg-red-500/10 border-red-500/20 text-red-400'
                  }`}
                >
                  <div>
                    <span className="font-semibold block">
                      {creationResult.status === 'active'
                        ? 'Document Approved & Indexed in Vector Store'
                        : 'Document Quarantined / Rejected by Quality Gate'}
                    </span>
                    <span className="text-[11px] opacity-80">
                      {creationResult.quarantine_reason || 'Quality scores passed threshold.'}
                    </span>
                  </div>
                </div>
              )}

              <div className="space-y-1">
                <label className="text-zinc-400 font-medium text-[11px] uppercase tracking-wider block">
                  Document Title
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Hardware Warranty Policy 2026"
                  className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 text-xs focus:outline-none focus:border-zinc-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-zinc-400 font-medium text-[11px] uppercase tracking-wider block">
                    Product Scope
                  </label>
                  <input
                    type="text"
                    value={product}
                    onChange={(e) => setProduct(e.target.value)}
                    className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 text-xs focus:outline-none focus:border-zinc-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-zinc-400 font-medium text-[11px] uppercase tracking-wider block">
                    Access Level Tier
                  </label>
                  <select
                    value={accessLevel}
                    onChange={(e) => setAccessLevel(e.target.value as DocumentAccessLevel)}
                    className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 text-xs focus:outline-none focus:border-zinc-500"
                  >
                    <option value="public">Public</option>
                    <option value="internal">Internal</option>
                    <option value="restricted">Restricted</option>
                    <option value="confidential">Confidential</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1">
                  <label className="text-zinc-400 font-medium text-[11px] uppercase tracking-wider block">Version</label>
                  <input
                    type="number"
                    min={1}
                    value={version}
                    onChange={(e) => setVersion(Number(e.target.value))}
                    className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 text-xs focus:outline-none focus:border-zinc-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-zinc-400 font-medium text-[11px] uppercase tracking-wider block">Effective Date</label>
                  <input
                    type="date"
                    value={effectiveDate}
                    onChange={(e) => setEffectiveDate(e.target.value)}
                    className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 text-xs focus:outline-none focus:border-zinc-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-zinc-400 font-medium text-[11px] uppercase tracking-wider block">Expiry Date</label>
                  <input
                    type="date"
                    value={expiryDate}
                    onChange={(e) => setExpiryDate(e.target.value)}
                    className="w-full px-3 py-1.5 rounded bg-zinc-900 border border-border text-zinc-200 text-xs focus:outline-none focus:border-zinc-500"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-zinc-400 font-medium text-[11px] uppercase tracking-wider block">
                  Policy Content / Evidence Text
                </label>
                <textarea
                  rows={4}
                  required
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Enter policy terms. Automated quality gates evaluate grounding, conflict detection, and prompt injection."
                  className="w-full p-2.5 rounded bg-zinc-900 border border-border text-zinc-200 text-xs font-mono focus:outline-none focus:border-zinc-500 leading-relaxed"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 rounded border border-border text-zinc-400 hover:text-zinc-200 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-3 py-1.5 rounded bg-zinc-100 text-zinc-950 hover:bg-white font-medium text-xs disabled:opacity-50 transition-colors"
                >
                  {submitting ? 'Running Quality Gate...' : 'Deploy to Pipeline'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Document Detail Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl bg-card border border-border rounded-lg shadow-xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="px-5 py-3.5 border-b border-border flex items-center justify-between bg-zinc-900/50">
              <h3 className="text-xs font-semibold text-zinc-100 uppercase tracking-wider">{selectedDoc.title}</h3>
              <button
                onClick={() => setSelectedDoc(null)}
                className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs overflow-y-auto">
              <div className="grid grid-cols-2 gap-2.5 p-3 rounded bg-zinc-900/60 border border-border text-zinc-300">
                <div>ID: <span className="font-mono text-zinc-200">{selectedDoc.id}</span></div>
                <div>Status: <span className="font-mono uppercase text-zinc-200">{selectedDoc.status}</span></div>
                <div>Access Tier: <span className="capitalize text-zinc-200">{selectedDoc.access_level}</span></div>
                <div>Version: <span className="font-mono text-zinc-200">v{selectedDoc.version}</span></div>
                <div>Effective: <span className="font-mono text-zinc-200">{new Date(selectedDoc.effective_date).toLocaleDateString()}</span></div>
                <div>Expiry: <span className="font-mono text-zinc-200">{selectedDoc.expiry_date ? new Date(selectedDoc.expiry_date).toLocaleDateString() : 'Permanent'}</span></div>
              </div>

              <div className="space-y-1">
                <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                  Grounding Policy Text:
                </span>
                <div className="p-3.5 rounded bg-zinc-950 border border-border text-zinc-200 font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
                  {selectedDoc.content}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
