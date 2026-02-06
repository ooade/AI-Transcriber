import React from 'react';
import { Mic, Square, Loader2 } from 'lucide-react';
import { APP_TEXT } from '../constants/text';
import { useRecording } from '../contexts/RecordingContext.tsx';

interface AudioRecorderProps {}

const AudioRecorder: React.FC<AudioRecorderProps> = () => {
	const { status, duration, isProcessing, startRecording, stopRecording } =
		useRecording();

	const formatDuration = (seconds: number): string => {
		const mins = Math.floor(seconds / 60);
		const secs = seconds % 60;
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	};

	const isDisabled = status !== 'idle' || isProcessing;

	return (
		<div className="flex flex-col items-center space-y-8 py-4">
			{/* 1. Main Action Button */}
			<div className="relative group">
				{status === 'idle' && !isProcessing && (
					<button
						onClick={startRecording}
						disabled={isDisabled}
						className="flex items-center gap-3 px-8 py-4 bg-[var(--accent-primary)] text-white rounded-xl font-bold text-sm shadow-[0_8px_20px_rgba(88,101,242,0.3)] hover:shadow-[0_12px_28px_rgba(88,101,242,0.4)] hover:-translate-y-0.5 transition-all active:scale-95 active:translate-y-0"
					>
						<Mic className="w-6 h-6" />
						{APP_TEXT.AUDIO_RECORDER.START_BUTTON}
					</button>
				)}

				{(status === 'recording' ||
					status === 'initializing' ||
					status === 'stopping') && (
					<button
						onClick={stopRecording}
						disabled={status === 'stopping' || status === 'initializing'}
						className="flex items-center gap-3 px-8 py-4 bg-[var(--accent-danger)] text-white rounded-xl font-bold text-sm shadow-[0_8px_20px_rgba(242,63,67,0.3)] hover:shadow-[0_12px_28px_rgba(242,63,67,0.4)] hover:-translate-y-0.5 transition-all active:scale-95 active:translate-y-0"
					>
						<div className="relative">
							<Square className="w-6 h-6 fill-current" />
							<div className="absolute inset-0 bg-white rounded-full animate-ping opacity-20 scale-150" />
						</div>
						{APP_TEXT.AUDIO_RECORDER.STOP_BUTTON}
					</button>
				)}

				{isProcessing && (
					<button
						disabled
						className="flex items-center gap-3 px-8 py-4 bg-[var(--bg-sidebar)] border border-[rgba(255,255,255,0.05)] text-[var(--text-muted)] rounded-xl font-bold text-sm shadow-inner cursor-wait opacity-80"
					>
						<Loader2 className="w-6 h-6 animate-spin" />
						{APP_TEXT.RECORDER.PROCESSING}
					</button>
				)}
			</div>

			{/* 2. Feedback Area (Timer & Status) */}
			{(status === 'recording' || status === 'stopping') && (
				<div className="flex flex-col items-center gap-4 animate-in fade-in slide-in-from-top-2 duration-300">
					<div className="text-5xl font-black text-white tabular-nums tracking-tighter drop-shadow-sm">
						{formatDuration(duration)}
					</div>
					<div className="inline-flex items-center gap-2.5 px-3 py-1 bg-[rgba(0,0,0,0.2)] border border-[rgba(255,255,255,0.03)] rounded-full text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-wider shadow-inner">
						<div className="w-1.5 h-1.5 bg-[var(--accent-danger)] rounded-full animate-pulse shadow-[0_0_8px_rgba(242,63,67,0.5)]" />
						{status === 'stopping'
							? APP_TEXT.RECORDER.FINALIZING
							: APP_TEXT.RECORDER.RECORDING}
					</div>
				</div>
			)}
		</div>
	);
};

export default AudioRecorder;
