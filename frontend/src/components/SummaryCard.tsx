import React, { useState, useEffect } from 'react';
import { useServerEvents } from '../contexts/ServerEventsContext';
import { endpoints } from '../config';
import { APP_TEXT } from '../constants/text';
import { AlertCircle, RefreshCcw, Cpu, ListChecks, Copy, Check, Maximize2, Minimize2 } from 'lucide-react';
import { cn } from '../utils/cn';

interface SummaryCardProps {
    transcript: {
        id: string;
        summary?: string;
        summary_model?: string;
        error?: string;
        meeting_type?: string;
    };
    isFullMode?: boolean;
    onToggleFullMode?: () => void;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({
    transcript,
    isFullMode = false,
    onToggleFullMode
}) => {
    const [summary, setSummary] = useState<string | null>(transcript.summary || null);
    const [model, setModel] = useState<string | null>(transcript.summary_model || transcript.meeting_type || null);
    const [loading, setLoading] = useState(!transcript.summary && !transcript.error);
    const [error, setError] = useState<boolean>(false);
    const [attempts, setAttempts] = useState(0);
    const [statusMessage, setStatusMessage] = useState<string>(APP_TEXT.SUMMARY.DEFAULT_LOADING);
    const [copied, setCopied] = useState(false);

    const MAX_ATTEMPTS = 180;

    const { subscribe } = useServerEvents();

    useEffect(() => {
        if (transcript.summary) {
             setSummary(transcript.summary);
             setModel(transcript.summary_model || transcript.meeting_type || null);
             setLoading(false);
        }
    }, [transcript.summary, transcript.summary_model, transcript.meeting_type]);

    useEffect(() => {
        if (summary) return;

        const unsubscribe = subscribe('summary_complete', (payload: any) => {
             if (payload.id === transcript.id) {
                 setSummary(payload.summary);
                 setModel(payload.meeting_type);
                 setLoading(false);
                 setError(false);
             }
        });

        const unsubscribeFailure = subscribe('summary_failed', (payload: any) => {
             if (payload.id === transcript.id) {
                 setLoading(false);
                 setError(true);
             }
        });

        const unsubscribeProgress = subscribe('task_progress', (payload: any) => {
             if (payload.id === transcript.id && payload.message) {
                 setStatusMessage(payload.message);
             }
        });

        const interval = setInterval(() => {
            if (attempts >= MAX_ATTEMPTS) {
                setLoading(false);
                setError(true);
                clearInterval(interval);
                return;
            }
            setAttempts(prev => prev + 1);
        }, 3000);

        return () => {
            unsubscribe();
            unsubscribeFailure();
            unsubscribeProgress();
            clearInterval(interval);
        };
    }, [transcript.id, summary, attempts, subscribe]);

    const handleCopy = () => {
        if (!summary) return;
        navigator.clipboard.writeText(summary);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleRetry = async () => {
        setLoading(true);
        setError(false);
        setAttempts(0);

        try {
            await fetch(endpoints.transcriptionSummarize(transcript.id), {
                method: 'POST'
            });
        } catch (e) {
            setLoading(false);
            setError(true);
        }
    };

    if (loading) {
        return (
            <div className="p-8 bg-[var(--bg-sidebar)] border border-[rgba(0,0,0,0.2)] shadow-md rounded-xl">
                <div className="flex items-center gap-6">
                     <div className="w-8 h-8 border-[3px] border-[var(--accent-primary)]/20 border-t-[var(--accent-primary)] rounded-full animate-spin" />
                     <div className="flex-1">
                        <h3 className="text-sm font-bold tracking-tight text-[var(--text-primary)]">
                            {statusMessage}
                        </h3>
                        <p className="text-[10px] font-bold text-[var(--text-muted)] uppercase mt-1.5 opacity-60">
                            Saving recording
                        </p>
                     </div>
                </div>
            </div>
        );
    }

    if (error && !summary) {
         return (
            <div className="p-8 bg-red-500/5 border border-[var(--accent-danger)]/20 shadow-sm rounded-xl">
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-5">
                        <div className="p-2.5 bg-[var(--accent-danger)]/10 rounded-lg">
                            <AlertCircle className="w-6 h-6 text-[var(--accent-danger)]" />
                        </div>
                        <div>
                            <h3 className="text-xs font-bold text-[var(--accent-danger)] uppercase tracking-widest">{APP_TEXT.SUMMARY.DELAY_TITLE}</h3>
                            <p className="text-[11px] text-[var(--text-secondary)] mt-1">{APP_TEXT.SUMMARY.DELAY_MSG}</p>
                        </div>
                    </div>
                    <button
                        onClick={handleRetry}
                        className="p-2.5 hover:bg-[var(--accent-danger)]/10 text-[var(--accent-danger)] transition-colors rounded-lg"
                    >
                        <RefreshCcw className="w-5 h-5" />
                    </button>
                </div>
            </div>
        );
    }

    if (!summary) return null;

    return (
        <div className="bg-[var(--bg-sidebar)] border border-[rgba(0,0,0,0.2)] shadow-lg rounded-xl overflow-hidden">
             <div className="px-6 py-4 border-b border-[rgba(0,0,0,0.2)] bg-[rgba(0,0,0,0.1)] flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-[var(--accent-primary)]/10 rounded-lg">
                        <ListChecks className="w-5 h-5 text-[var(--accent-primary)]" />
                    </div>
                    <h2 className="text-xs font-bold tracking-tight text-white uppercase">
                      {APP_TEXT.SUMMARY.TITLE}
                    </h2>
                </div>
                <div className="flex items-center gap-2">
                    {model && isFullMode && (
                        <div className="flex items-center gap-2 px-3 py-1 bg-[var(--bg-rail)] border border-[rgba(255,255,255,0.02)] rounded-md mr-1">
                            <Cpu className="w-4 h-4 text-[var(--text-muted)]" />
                            <span className="text-[10px] font-bold text-[var(--text-secondary)] uppercase">
                                {model}
                            </span>
                        </div>
                    )}

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
            </div>
            <div className="p-8 text-[15px] text-[var(--text-secondary)] leading-[1.8] space-y-6">
                 {summary.split('\n').filter(l => l.trim()).map((line, i) => (
                    <p key={i} className={cn(
                        "relative group",
                        line.startsWith('- **') && "pl-6 py-0.5"
                    )}>
                        {line.startsWith('- **') ? (
                            <>
                                <span className="absolute left-0 top-3 w-1.5 h-1.5 bg-[var(--accent-primary)] rounded-full shadow-[0_0_8px_rgba(88,101,242,0.6)] group-hover:scale-125 transition-transform" />
                                <strong className="font-bold text-white mr-1">{line.split('**:')[0].replace('- **', '')}:</strong>
                                <span className="text-[var(--text-secondary)]"> {line.split('**:')[1]}</span>
                            </>
                        ) : (
                            line
                        )}
                    </p>
                 ))}
            </div>
        </div>
    );
};
