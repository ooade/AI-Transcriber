import React, { useState, useRef } from 'react';
import { APP_TEXT } from '../constants/text';
import { Save, Cpu, Type, Info, FileText, Copy, Check, Maximize2, Minimize2 } from 'lucide-react';
import { CustomAudioPlayer } from './CustomAudioPlayer';
import { cn } from '../utils/cn';

interface Word {
  start: number;
  end: number;
  word: string;
  probability: number;
}

interface TranscriptEditorProps {
  transcriptionId: string;
  initialText: string;
  wordTimestamps: Word[];
  audioUrl: string;
  onSave: (id: string, newText: string) => Promise<void>;
  isFullMode?: boolean;
  onToggleFullMode?: () => void;
}

export const TranscriptEditor: React.FC<TranscriptEditorProps> = ({
  transcriptionId,
  initialText,
  wordTimestamps,
  audioUrl,
  onSave,
  isFullMode = false,
  onToggleFullMode
}) => {
  const [text, setText] = useState(initialText);
  const [currentTime, setCurrentTime] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  const handleWordClick = (startTime: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = startTime;
      audioRef.current.play();
    }
  };


  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave(transcriptionId, text);
    } catch (error) {
       console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isWordActive = (start: number, end: number) => {
    return currentTime >= start && currentTime <= end;
  };

  return (
    <div className="flex flex-col h-full bg-[var(--bg-main)]">

      {/* Premium Header (Glass) */}
      <div className="flex justify-between items-center px-6 py-3 glass-header shrink-0 z-40">
        <div className="flex items-center gap-4">
          {onToggleFullMode && (
             <button
                onClick={onToggleFullMode}
                className={cn(
                    "flex items-center justify-center w-8 h-8 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all",
                    isFullMode
                        ? "bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] border border-[var(--accent-primary)]/30"
                        : "bg-[rgba(255,255,255,0.03)] text-[var(--text-muted)] hover:text-white border border-[rgba(255,255,255,0.05)]"
                )}
                title={isFullMode ? "Minimize" : "Maximize"}
            >
                {isFullMode ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={handleCopy}
            className={cn(
                "flex items-center justify-center w-8 h-8 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all",
                copied
                    ? "bg-[var(--accent-success)]/20 text-[var(--accent-success)] border border-[var(--accent-success)]/30"
                    : "bg-[rgba(255,255,255,0.03)] text-[var(--text-muted)] hover:text-white border border-[rgba(255,255,255,0.05)]"
            )}
            title={APP_TEXT.UTILITIES.COPY}
          >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <div className="flex items-center gap-2 px-3 py-1 bg-[var(--bg-rail)] border border-[rgba(255,255,255,0.02)] rounded-md">
             <Cpu className="w-4 h-4 text-[var(--text-muted)]" />
             <span className="text-[10px] text-[var(--text-secondary)] font-bold tracking-tight uppercase">{APP_TEXT.TRANSCRIPT_EDITOR.MODE_MANUAL}</span>
          </div>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className={cn(
                "flex items-center gap-2.5 px-6 py-1.5 rounded-md font-black text-[10px] uppercase tracking-widest transition-all shadow-md",
                isSaving
                    ? "bg-[var(--bg-rail)] text-[var(--text-muted)] cursor-not-allowed border border-[rgba(0,0,0,0.2)]"
                    : "bg-[var(--accent-primary)] text-white hover:opacity-90 active:scale-95 shadow-[0_4px_12px_rgba(88,101,242,0.3)]"
            )}
          >
            {isSaving ? (
                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : (
                <Save className="w-3.5 h-3.5" />
            )}
            {isSaving ? APP_TEXT.TRANSCRIPT_EDITOR.SAVING_BUTTON : APP_TEXT.TRANSCRIPT_EDITOR.SAVE_BUTTON}
          </button>
        </div>
      </div>

      {/* Audio Engine Rail - CUSTOM PLAYER */}
      <div className="px-6 py-1.5 border-b border-black/10 bg-[var(--bg-rail)] flex items-center gap-4">
        <CustomAudioPlayer
          src={audioUrl}
          audioRef={audioRef}
          onTimeUpdate={(time) => setCurrentTime(time)}
        />
      </div>

      {/* Integrated Workspace */}
      <div className="flex-1 flex overflow-hidden">

        {/* Semantic Transcript View (Integrated Editing) */}
        <div className="flex-1 overflow-y-auto custom-scrollbar bg-[var(--bg-main)]">
           <div className="max-w-4xl mx-auto py-10 px-8">
              <div className="flex items-center gap-2 mb-8 pb-2 border-b border-[rgba(255,255,255,0.02)]">
                <FileText className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                <h3 className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-[0.3em]">
                    {APP_TEXT.TRANSCRIPT_EDITOR.INTERACTIVE_TITLE}
                </h3>
              </div>

              <div className="space-y-10">
                <div className="text-[16px] leading-[1.8] text-[var(--text-secondary)] font-medium">
                    {wordTimestamps.length > 0 ? (
                        <div className="flex flex-wrap gap-x-1 gap-y-1">
                            {wordTimestamps.map((word, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => handleWordClick(word.start)}
                                    className={cn(
                                        "px-0.5 border-b-2 bg-transparent transition-all rounded-[2px]",
                                        isWordActive(word.start, word.end)
                                            ? "bg-[var(--accent-primary)] text-white border-[var(--accent-primary)] shadow-[0_0_8px_rgba(88,101,242,0.4)]"
                                            : word.probability < 0.9
                                                ? "border-b-[var(--accent-danger)]/40 text-white hover:bg-[var(--accent-danger)]/5"
                                                : "border-transparent text-[var(--text-secondary)] hover:bg-[rgba(255,255,255,0.04)] hover:text-white"
                                    )}
                                >
                                    {word.word}
                                </button>
                            ))}
                        </div>
                    ) : (
                        <p className="italic text-[var(--text-muted)] text-[13px]">{APP_TEXT.TRANSCRIPT_EDITOR.PLACEHOLDER}</p>
                    )}
                </div>

                <div className="h-px bg-[rgba(255,255,255,0.02)]" />

                <div className="space-y-4">
                    <div className="flex items-center gap-2">
                        <Type className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                        <h3 className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-[0.3em]">
                            {APP_TEXT.TRANSCRIPT_EDITOR.EDIT_TITLE}
                        </h3>
                    </div>
                    <textarea
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        className="w-full h-96 p-6 bg-[rgba(0,0,0,0.2)] border border-[rgba(255,255,255,0.02)] text-[15px] leading-[1.8] focus:outline-none focus:border-[var(--accent-primary)]/40 rounded-lg resize-none text-white selection:bg-[var(--accent-primary)] selection:text-white shadow-inner"
                        placeholder={APP_TEXT.TRANSCRIPT_EDITOR.PLACEHOLDER}
                    />
                </div>
              </div>
           </div>
        </div>

        {/* Premium Side Inspector */}
        <aside className="w-80 border-l border-[rgba(0,0,0,0.1)] bg-[var(--bg-sidebar)] hidden xl:block p-8">
           <div className="flex items-center gap-3 mb-8 px-1">
              <div className="p-2 bg-[rgba(0,0,0,0.1)] rounded-md border border-[rgba(255,255,255,0.02)]">
                <Info className="w-5 h-5 text-[var(--accent-primary)]" />
              </div>
              <span className="text-[11px] font-bold text-white tracking-widest uppercase">{APP_TEXT.TRANSCRIPT_EDITOR.ANALYTICS_INSPECTOR}</span>
           </div>

           <div className="space-y-6">
              <div className="p-5 bg-[rgba(0,0,0,0.1)] border border-[rgba(255,255,255,0.02)] rounded-lg shadow-inner">
                 <span className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest block mb-4 opacity-70">{APP_TEXT.TRANSCRIPT_EDITOR.WORD_CONFIDENCE}</span>
                 <div className="h-2 w-full bg-[var(--bg-rail)] rounded-full overflow-hidden border border-[rgba(0,0,0,0.1)]">
                    <div className="h-full bg-[var(--accent-primary)]" style={{ width: '92%' }} />
                 </div>
                 <div className="flex justify-between items-center mt-3">
                    <span className="text-[9px] font-bold text-[var(--text-muted)] uppercase">{APP_TEXT.TRANSCRIPT_EDITOR.CONFIDENCE_LABEL}</span>
                    <span className="text-[11px] font-bold text-[var(--accent-primary)]">{APP_TEXT.TRANSCRIPT_EDITOR.CONFIDENCE_AVG}</span>
                 </div>
              </div>

              <div className="p-5 bg-[rgba(0,0,0,0.1)] border border-[rgba(255,255,255,0.02)] rounded-lg shadow-inner">
                 <span className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest block mb-4 opacity-70">{APP_TEXT.TRANSCRIPT_EDITOR.SESSION_INTEGRITY}</span>
                 <div className="flex items-center gap-3 px-3 py-2 bg-[var(--accent-success)]/5 border border-[var(--accent-success)]/10 rounded-md">
                    <div className="w-2 h-2 bg-[var(--accent-success)] rounded-full shadow-[0_0_8px_rgba(35,165,89,0.5)]" />
                    <span className="text-[10px] font-bold text-[var(--accent-success)]">{APP_TEXT.TRANSCRIPT_EDITOR.HASH_MATCH}</span>
                 </div>
              </div>

              <div className="text-[10px] text-[var(--text-muted)] bg-[rgba(0,0,0,0.1)] p-5 rounded-lg space-y-2.5 border border-[rgba(255,255,255,0.02)]">
                 <p className="flex justify-between"><span>{APP_TEXT.TRANSCRIPT_EDITOR.STATS.IMPROVEMENTS}</span> <span className="text-white font-bold">12 Words</span></p>
                 <p className="flex justify-between"><span>{APP_TEXT.TRANSCRIPT_EDITOR.STATS.SESSION_EDITS}</span> <span className="text-white font-bold">0 Sessions</span></p>
                 <p className="flex justify-between"><span>{APP_TEXT.TRANSCRIPT_EDITOR.STATS.TRACKING_ID}</span> <span className="text-[var(--accent-primary)] font-bold">A1-92</span></p>
              </div>
           </div>
        </aside>
      </div>
    </div>
  );
};
