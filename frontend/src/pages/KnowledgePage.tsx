import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Plus,
  Search,
  ShieldCheck,
  ShieldAlert,
  Calendar,
  Lock,
  Layers,
  CheckCircle,
  XCircle,
  FileText,
  RotateCw,
  ExternalLink,
  X,
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
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground tracking-tight">
            Knowledge Base Pipeline & Policy Store
          </h1>
          <p className="text-xs text-muted-foreground">
            Manage enterprise documentation, temporal warranty policies, and automated quality gates.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleSyncKnowledge}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-muted text-xs font-medium text-foreground transition-all"
          >
            <RotateCw className="w-3.5 h-3.5" />
            <span>Sync Knowledge Store</span>
          </button>
          <button
            onClick={() => {
              setCreationResult(null);
              setShowAddModal(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold shadow-sm hover:opacity-90 transition-opacity"
          >
            <Plus className="w-4 h-4" />
            <span>Add New Policy Document</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-card border border-border shadow-sm grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search policies by keyword or product..."
            className="w-full pl-8 pr-3 py-1.5 rounded-md bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div>
          <select
            value={accessFilter}
            onChange={(e) => setAccessFilter(e.target.value)}
            className="w-full px-3 py-1.5 rounded-md bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">All Access Levels</option>
            <option value="public">Public Access</option>
            <option value="internal">Internal Only</option>
            <option value="restricted">Restricted Tier</option>
            <option value="confidential">Confidential</option>
          </select>
        </div>

        <div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full px-3 py-1.5 rounded-md bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
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
              className={`p-5 rounded-xl bg-card border transition-all cursor-pointer hover:border-primary/40 shadow-sm flex flex-col justify-between space-y-4 ${
                isQuarantined
                  ? 'border-rose-500/40 bg-rose-500/5'
                  : isFailed
                  ? 'border-amber-500/40 bg-amber-500/5'
                  : 'border-border'
              }`}
            >
              <div className="space-y-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div
                      className={`p-1.5 rounded-md border ${
                        isQuarantined
                          ? 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                          : 'bg-primary/10 text-primary border-primary/20'
                      }`}
                    >
                      {isQuarantined ? (
                        <ShieldAlert className="w-4 h-4" />
                      ) : (
                        <BookOpen className="w-4 h-4" />
                      )}
                    </div>
                    <span className="text-[10px] font-mono text-muted-foreground">{doc.id}</span>
                  </div>

                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase ${
                      doc.status === 'active'
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                        : doc.status === 'quarantined'
                        ? 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30'
                        : 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30'
                    }`}
                  >
                    {doc.status}
                  </span>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-foreground line-clamp-1">{doc.title}</h3>
                  <p className="text-xs text-muted-foreground line-clamp-3 mt-1.5 leading-relaxed">
                    {doc.content}
                  </p>
                </div>
              </div>

              {/* Quality Gate / Metadata Footer */}
              <div className="pt-3 border-t border-border/60 space-y-2 text-[11px]">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="flex items-center gap-1 font-medium">
                    <Layers className="w-3 h-3" /> Version {doc.version}
                  </span>
                  <span className="capitalize font-medium text-foreground px-1.5 py-0.5 bg-muted rounded">
                    {doc.access_level}
                  </span>
                </div>

                {doc.quarantine_reason && (
                  <div className="text-[11px] font-medium text-rose-500 line-clamp-2">
                    {doc.quarantine_reason}
                  </div>
                )}

                <div className="flex items-center justify-between text-muted-foreground pt-1">
                  <span>Product: <strong className="text-foreground">{doc.product}</strong></span>
                  <span>Effective: {new Date(doc.effective_date).toLocaleDateString()}</span>
                </div>
              </div>
            </div>
          );
        })}
        {documents.length === 0 && !loading && (
          <div className="col-span-full p-12 text-center text-muted-foreground text-xs">
            No knowledge base documents match your criteria.
          </div>
        )}
      </div>

      {/* Add Document Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl bg-card border border-border rounded-2xl shadow-xl overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-muted/30">
              <div className="flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-primary" />
                <h3 className="text-sm font-bold text-foreground">Add Knowledge Policy Document</h3>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-md text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateDocument} className="p-6 space-y-4 text-xs">
              {creationResult && (
                <div
                  className={`p-3 rounded-lg border text-xs flex items-center gap-2 ${
                    creationResult.status === 'active'
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                      : 'bg-rose-500/10 border-rose-500/20 text-rose-600 dark:text-rose-400'
                  }`}
                >
                  {creationResult.status === 'active' ? (
                    <CheckCircle className="w-4 h-4 shrink-0" />
                  ) : (
                    <XCircle className="w-4 h-4 shrink-0" />
                  )}
                  <div>
                    <span className="font-semibold block">
                      {creationResult.status === 'active'
                        ? 'Document Approved & Indexed!'
                        : 'Document Quarantined / Rejected'}
                    </span>
                    <span className="text-[11px] opacity-90">
                      {creationResult.quarantine_reason ||
                        `Quality Test: Accuracy ${Math.round(
                          (creationResult.accuracy_score || 0.95) * 100
                        )}%, Grounding ${Math.round(
                          (creationResult.grounding_score || 0.9) * 100
                        )}%`}
                    </span>
                  </div>
                </div>
              )}

              <div className="space-y-1">
                <label className="font-semibold text-foreground">Document Title:</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Return Policy 2026 or UltraLaptop Liquid Protection Terms"
                  className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-semibold text-foreground">Product Code / Line:</label>
                  <input
                    type="text"
                    value={product}
                    onChange={(e) => setProduct(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-semibold text-foreground">Access Level Tier:</label>
                  <select
                    value={accessLevel}
                    onChange={(e) => setAccessLevel(e.target.value as DocumentAccessLevel)}
                    className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground text-xs"
                  >
                    <option value="public">Public (General Customers)</option>
                    <option value="internal">Internal (Support Agents)</option>
                    <option value="restricted">Restricted (Management)</option>
                    <option value="confidential">Confidential (Executive Settlement)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1">
                  <label className="font-semibold text-foreground">Version:</label>
                  <input
                    type="number"
                    min={1}
                    value={version}
                    onChange={(e) => setVersion(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-semibold text-foreground">Effective Date:</label>
                  <input
                    type="date"
                    value={effectiveDate}
                    onChange={(e) => setEffectiveDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-semibold text-foreground">Expiry Date:</label>
                  <input
                    type="date"
                    value={expiryDate}
                    onChange={(e) => setExpiryDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-muted/40 border border-border text-foreground text-xs"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-foreground">Document Content / Text:</label>
                <textarea
                  rows={5}
                  required
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Enter policy terms. Automated quality gates will evaluate accuracy (>= 0.85), grounding (>= 0.80), and test for embedded prompt injection."
                  className="w-full p-3 rounded-lg bg-muted/40 border border-border text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary font-mono leading-relaxed"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-lg border border-border text-muted-foreground hover:text-foreground text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-semibold text-xs shadow-sm hover:opacity-90 disabled:opacity-50"
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
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl bg-card border border-border rounded-2xl shadow-xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-muted/30">
              <div className="flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-primary" />
                <h3 className="text-sm font-bold text-foreground">{selectedDoc.title}</h3>
              </div>
              <button
                onClick={() => setSelectedDoc(null)}
                className="p-1 rounded-md text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs overflow-y-auto">
              <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-muted/40 border border-border">
                <div>ID: <span className="font-mono text-foreground font-medium">{selectedDoc.id}</span></div>
                <div>Status: <span className="font-semibold text-primary uppercase">{selectedDoc.status}</span></div>
                <div>Access Tier: <span className="capitalize text-foreground font-medium">{selectedDoc.access_level}</span></div>
                <div>Version: <span className="font-medium text-foreground">v{selectedDoc.version}</span></div>
                <div>Effective: <span className="text-foreground">{new Date(selectedDoc.effective_date).toLocaleDateString()}</span></div>
                <div>Expiry: <span className="text-foreground">{selectedDoc.expiry_date ? new Date(selectedDoc.expiry_date).toLocaleDateString() : 'Permanent'}</span></div>
              </div>

              <div className="space-y-1">
                <span className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider block">
                  Grounding Policy Content:
                </span>
                <div className="p-4 rounded-xl bg-card border border-border text-foreground leading-relaxed font-mono whitespace-pre-wrap">
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

