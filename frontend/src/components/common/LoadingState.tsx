import React from 'react';
import { cn } from '../../utils/cn';

interface LoadingStateProps {
    message?: string;
    className?: string;
    fullHeight?: boolean;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
    message = "Processing Data...",
    className,
    fullHeight = false
}) => {
    return (
        <div className={cn(
            "flex flex-col items-center justify-center space-y-6",
            fullHeight ? "min-h-[60vh]" : "h-96",
            className
        )}>
            {/* Premium Neural Spinner */}
            <div className="relative w-12 h-12">
                {/* Background Ring */}
                <div className="absolute inset-0 rounded-full border-2 border-[var(--accent-primary)]/10" />

                {/* Spinning Segment */}
                <div className="absolute inset-0 rounded-full border-2 border-t-[var(--accent-primary)] border-r-transparent border-b-transparent border-l-transparent animate-spin" />

                {/* Inner Pulsing Node */}
                <div className="absolute inset-3 bg-[var(--accent-primary)] rounded-none rotate-45 animate-pulse opacity-40 shadow-[0_0_15px_rgba(88,101,242,0.5)]" />

                {/* Secondary Orbit */}
                <div className="absolute inset-1 rounded-full border border-dashed border-[var(--text-muted)]/20 animate-[spin_3s_linear_infinite]" />
            </div>

            <div className="flex flex-col items-center gap-2">
                <p className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-[0.3em] animate-pulse">
                    {message}
                </p>
                <div className="flex gap-1">
                    <span className="w-1 h-1 bg-[var(--accent-primary)]/40 rounded-full animate-bounce [animation-delay:-0.3s]" />
                    <span className="w-1 h-1 bg-[var(--accent-primary)]/40 rounded-full animate-bounce [animation-delay:-0.15s]" />
                    <span className="w-1 h-1 bg-[var(--accent-primary)]/40 rounded-full animate-bounce" />
                </div>
            </div>
        </div>
    );
};
