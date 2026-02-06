import React, { useState } from 'react';
import { APP_TEXT } from '../constants/text';
import { Calendar, Database, Search, ChevronRight, Shield, Pencil, Check, X } from 'lucide-react';
import { LoadingState } from './common/LoadingState';

interface HistoryItem {
  id: string;
  title: string;
  created_at: string;
  duration_seconds: number;
  language: string;
  preview?: string;
  summary?: string;
  meeting_type?: string;
}

interface HistoryViewProps {
  history: HistoryItem[];
  onSelectItem: (id: string) => void;
  onRename: (id: string, newTitle: string) => Promise<void>;
  isLoading: boolean;
}

export const HistoryView: React.FC<HistoryViewProps> = ({ history, onSelectItem, onRename, isLoading }) => {
  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);

  const formatDuration = (seconds: number): string => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const filteredItems = history.filter(item =>
    ((item.title || item.summary || item.preview || '').toLowerCase().includes(search.toLowerCase()) ||
    item.id.toLowerCase().includes(search.toLowerCase()))
  );

  const startEdit = (e: React.MouseEvent, item: HistoryItem) => {
    e.stopPropagation();
    setEditingId(item.id);
    setEditValue(item.title || '');
  };

  const cancelEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
    setEditValue('');
  };

  const handleRename = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!editValue.trim() || isUpdating) return;

    setIsUpdating(true);
    try {
        await onRename(id, editValue.trim());
        setEditingId(null);
    } catch (error) {
        console.error("Failed to rename:", error);
    } finally {
        setIsUpdating(false);
    }
  };

  if (isLoading) {
    return (
      <LoadingState message={APP_TEXT.HISTORY.LOADING} />
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-none">

      {/* Global Command Center / Library Filter */}
      <div className="space-y-6">
        <div className="flex items-end justify-between px-1">
            <div>
                <span className="text-[10px] font-bold text-[var(--accent-primary)] uppercase tracking-[0.2em] mb-1 block">{APP_TEXT.HISTORY_VIEW.ARCHIVE_INDEX}</span>
                <h2 className="text-4xl font-black tracking-tight text-white">{APP_TEXT.HISTORY.TITLE}</h2>
            </div>
            <div className="flex items-center gap-4">
                <div className="flex flex-col items-end">
                    <span className="text-[10px] text-[var(--text-muted)] uppercase font-bold tracking-widest leading-none opacity-60">{APP_TEXT.HISTORY_VIEW.STATUS_SYNCED}</span>
                    <span className="text-[11px] text-[var(--text-secondary)] mt-1.5 font-bold">{history.length} {history.length === 1 ? APP_TEXT.HISTORY_VIEW.COUNT_LABEL_SINGULAR : APP_TEXT.HISTORY_VIEW.COUNT_LABEL}</span>
                </div>
                <div className="w-10 h-10 bg-[var(--bg-rail)] border border-[rgba(0,0,0,0.2)] rounded-lg flex items-center justify-center shadow-md">
                    <Shield className="w-5 h-5 text-[var(--accent-success)]" />
                </div>
            </div>
        </div>

        <div className="relative group max-w-xl">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)] group-focus-within:text-[var(--accent-primary)] transition-colors" />
          <input
            type="text"
            placeholder={APP_TEXT.HISTORY.SEARCH_PLACEHOLDER}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-6 py-2.5 bg-[rgba(0,0,0,0.2)] border border-[rgba(255,255,255,0.02)] rounded-lg text-sm placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-primary)]/40 transition-all shadow-inner text-white"
          />
        </div>
      </div>

      {/* Modern Data Grid (Discord Style) */}
      <div className="bg-[var(--bg-sidebar)] border border-[rgba(0,0,0,0.2)] rounded-lg overflow-hidden shadow-lg">
        <table className="w-full text-left border-collapse font-sans">
            <thead>
                <tr className="bg-[rgba(0,0,0,0.1)] border-b border-[rgba(0,0,0,0.2)]">
                    <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)] w-16">#</th>
                    <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">{APP_TEXT.HISTORY_VIEW.TABLE_HEADERS.SUMMARY}</th>
                    <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">{APP_TEXT.HISTORY_VIEW.TABLE_HEADERS.DATE}</th>
                    <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">{APP_TEXT.HISTORY_VIEW.TABLE_HEADERS.DURATION}</th>
                    <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)] text-right">{APP_TEXT.HISTORY_VIEW.TABLE_HEADERS.ACTION}</th>
                </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(0,0,0,0.05)]">
                {filteredItems.length === 0 ? (
                    <tr>
                        <td colSpan={5} className="py-24 text-center">
                            <Database className="w-12 h-12 text-[rgba(255,255,255,0.05)] mx-auto mb-4" />
                            <p className="text-[var(--text-muted)] text-[11px] font-bold uppercase tracking-[0.2em]">{APP_TEXT.HISTORY.EMPTY_STATE}</p>
                        </td>
                    </tr>
                ) : (
                    filteredItems.map((item, idx) => (
                        <tr
                            key={item.id}
                            onClick={() => onSelectItem(item.id)}
                            className="group cursor-pointer hover:bg-[rgba(255,255,255,0.01)] transition-colors active:bg-[rgba(255,255,255,0.02)]"
                        >
                            <td className="px-6 py-5 font-bold text-[11px] text-[var(--text-muted)] opacity-40">{idx + 1}</td>
                            <td className="px-6 py-5">
                                <div className="flex flex-col gap-0.5">
                                    {editingId === item.id ? (
                                        <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                                            <input
                                                autoFocus
                                                value={editValue}
                                                onChange={e => setEditValue(e.target.value)}
                                                className="bg-[rgba(255,255,255,0.05)] border border-[var(--accent-primary)]/40 rounded px-2 py-1 text-sm text-white focus:outline-none w-full max-w-xs"
                                                onKeyDown={e => {
                                                    if (e.key === 'Enter') handleRename(e as any, item.id);
                                                    if (e.key === 'Escape') cancelEdit(e as any);
                                                }}
                                            />
                                            <button
                                                onClick={e => handleRename(e, item.id)}
                                                disabled={isUpdating}
                                                className="p-1 hover:bg-white/5 rounded text-[var(--accent-success)]"
                                            >
                                                <Check className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={cancelEdit}
                                                className="p-1 hover:bg-white/5 rounded text-[var(--text-muted)]"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 group/title">
                                            <span className="text-sm font-bold text-white group-hover:text-[var(--accent-primary)] transition-colors">
                                                {item.title || item.summary || item.preview || APP_TEXT.HISTORY.UNTITLED}
                                            </span>
                                            <button
                                                onClick={e => startEdit(e, item)}
                                                className="opacity-0 group-hover/title:opacity-40 hover:opacity-100 transition-opacity p-1"
                                            >
                                                <Pencil className="w-3 h-3 text-[var(--text-muted)]" />
                                            </button>
                                        </div>
                                    )}
                                    <span className="text-[10px] text-[var(--text-muted)] tracking-wider opacity-40">ID: {item.id.split('-')[0]}</span>
                                </div>
                            </td>
                            <td className="px-6 py-5">
                                <div className="flex items-center gap-2 text-[12px] text-[var(--text-secondary)] font-medium">
                                    <Calendar className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                                    {new Date(item.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                                </div>
                            </td>
                            <td className="px-6 py-5">
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-[var(--accent-primary)]/5 border border-[var(--accent-primary)]/10 text-[11px] font-bold text-[var(--accent-primary)] tabular-nums">
                                    {formatDuration(item.duration_seconds)}
                                </span>
                            </td>
                            <td className="px-6 py-5 text-right">
                                <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-[var(--bg-rail)] border border-[rgba(255,255,255,0.03)] rounded text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)] group-hover:bg-[var(--accent-primary)] group-hover:text-white group-hover:border-[var(--accent-primary)] group-hover:shadow-[0_4px_12px_rgba(88,101,242,0.3)] transition-all">
                                    {APP_TEXT.HISTORY_VIEW.ACTION_OPEN} <ChevronRight className="w-4 h-4 translate-x-0 group-hover:translate-x-0.5 transition-transform" />
                                </div>
                            </td>
                        </tr>
                    ))
                )}
            </tbody>
        </table>
      </div>

      {/* Technical Footer */}
      <div className="flex justify-between items-center text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-[0.2em] px-2 opacity-40">
        <span>{APP_TEXT.HISTORY_VIEW.CLIENT_FOOTER}</span>
        <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-[var(--accent-success)] rounded-full shadow-[0_0_8px_rgba(35,165,89,0.5)]" />
            <span>{APP_TEXT.HISTORY_VIEW.NODE_ID}</span>
        </div>
      </div>
    </div>
  );
};
