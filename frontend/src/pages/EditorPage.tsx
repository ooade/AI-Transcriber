import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SummaryCard } from '../components/SummaryCard';
import { TranscriptEditor } from '../components/TranscriptEditor';
import { endpoints } from '../config';
import { APP_TEXT } from '../constants/text';
import { cn } from '../utils/cn';
import { ChevronLeft, AlertCircle, Pencil, Check, X } from 'lucide-react';
import { LoadingState } from '../components/common/LoadingState';
import { motion } from 'framer-motion';

interface EditorPageProps {
  sessionId: string;
  onBack: () => void;
}

export const EditorPage: React.FC<EditorPageProps> = ({ sessionId, onBack }) => {
  const queryClient = useQueryClient();

  const { data: details, isLoading, error } = useQuery({
    queryKey: ['transcription', sessionId],
    queryFn: async () => {
      const response = await fetch(endpoints.transcription(sessionId));
      if (!response.ok) throw new Error('Failed to fetch details');
      return response.json();
    },
    enabled: !!sessionId,
  });

  const handleSaveCorrection = async (id: string, content: string) => {
    const response = await fetch(endpoints.transcriptionCorrection(id), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    if (!response.ok) throw new Error('Failed to save correction');
    queryClient.invalidateQueries({ queryKey: ['transcription', id] });
  };
  const [expandedView, setExpandedView] = React.useState<'none' | 'transcript' | 'summary'>('none');

  const [isEditingTitle, setIsEditingTitle] = React.useState(false);
  const [titleValue, setTitleValue] = React.useState('');

  const renameMutation = useMutation({
    mutationFn: async ({ id, title }: { id: string; title: string }) => {
      const response = await fetch(endpoints.transcriptionTitle(id), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      if (!response.ok) throw new Error('Failed to update title');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transcription', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['history'] });
      setIsEditingTitle(false);
    },
  });

  const handleRename = async () => {
    if (!titleValue.trim()) return;
    await renameMutation.mutateAsync({ id: sessionId, title: titleValue.trim() });
  };

  const startEditing = () => {
     setTitleValue(details?.title || "Session Detail");
     setIsEditingTitle(true);
  };

  const currentAudioUrl = details?.audio_file_path
    ? endpoints.audio(details.audio_file_path)
    : '';

  if (isLoading) {
    return (
      <LoadingState fullHeight message="Retrieving Archive..." />
    );
  }

  if (error || !details) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4 px-6 text-center">
        <div className="p-4 bg-rose-50 dark:bg-rose-900/20 rounded-full">
          <AlertCircle className="w-8 h-8 text-rose-500" />
        </div>
        <h3 className="text-zinc-900 dark:text-zinc-100 font-display font-bold text-lg">
          Retrieval Error
        </h3>
        <p className="text-zinc-500 max-w-xs mx-auto text-sm">
          {APP_TEXT.EDITOR.ERROR}
        </p>
        <button
          onClick={onBack}
          className="mt-4 px-6 py-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-xl font-display font-bold text-sm transition-transform active:scale-95"
        >
          Return to Library
        </button>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8 pb-20"
    >
      {/* Detail Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-3 rounded-2xl bg-[var(--bg-rail)] border border-[rgba(255,255,255,0.05)] text-[var(--text-muted)] hover:text-white transition-all hover:bg-[rgba(255,255,255,0.03)] active:scale-90"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            {isEditingTitle ? (
                <div className="flex items-center gap-2">
                    <input
                        autoFocus
                        value={titleValue}
                        onChange={e => setTitleValue(e.target.value)}
                        className="text-3xl font-display font-black text-zinc-900 dark:text-zinc-50 tracking-tight bg-transparent border-b-2 border-[var(--accent-primary)] outline-none min-w-[300px]"
                        onKeyDown={e => {
                            if (e.key === 'Enter') handleRename();
                            if (e.key === 'Escape') setIsEditingTitle(false);
                        }}
                    />
                     <button
                        onClick={handleRename}
                        className="p-2 hover:bg-[rgba(255,255,255,0.03)] rounded-lg text-[var(--accent-success)]"
                    >
                        <Check className="w-6 h-6" />
                    </button>
                    <button
                        onClick={() => setIsEditingTitle(false)}
                        className="p-2 hover:bg-[rgba(255,255,255,0.03)] rounded-lg text-[var(--text-muted)]"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>
            ) : (
                <h2
                    onClick={startEditing}
                    className="text-3xl font-display font-black text-zinc-900 dark:text-zinc-50 tracking-tight cursor-pointer hover:text-[var(--accent-primary)] transition-colors group flex items-center gap-3"
                >
                    {details.title || "Session Detail"}
                    <Pencil className="w-5 h-5 opacity-0 group-hover:opacity-40 transition-opacity" />
                </h2>
            )}
            <p className="text-xs font-mono text-zinc-400 mt-1 uppercase tracking-widest">
              Engine Log: {sessionId.substring(0, 8)}...
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Summary & Insights */}
        {expandedView !== 'transcript' && (
          <div className={cn(expandedView === 'summary' ? "lg:col-span-12" : "lg:col-span-4 space-y-8 sticky top-8")}>
             <SummaryCard
                transcript={details}
                isFullMode={expandedView === 'summary'}
                onToggleFullMode={() => setExpandedView(expandedView === 'summary' ? 'none' : 'summary')}
             />
          </div>
        )}

        {/* Right Column: Transcript Editor */}
        {expandedView !== 'summary' && (
          <div className={cn(expandedView === 'transcript' ? "lg:col-span-12" : "lg:col-span-8")}>
              <TranscriptEditor
                  transcriptionId={sessionId}
                  initialText={details.text}
                  wordTimestamps={details.word_timestamps}
                  audioUrl={currentAudioUrl}
                  onSave={handleSaveCorrection}
                  isFullMode={expandedView === 'transcript'}
                  onToggleFullMode={() => setExpandedView(expandedView === 'transcript' ? 'none' : 'transcript')}
              />
          </div>
        )}
      </div>
    </motion.div>
  );
};
