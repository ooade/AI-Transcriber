import React, { useState } from 'react';
import AudioRecorder from '../components/AudioRecorder';
import AudioUploader from '../components/AudioUploader';
import TranscriptionSettings from '../components/TranscriptionSettings';
import { SummaryCard } from '../components/SummaryCard';
import { AudioPulse } from '../components/visualizations/AudioPulse';
import { APP_TEXT } from '../constants/text';
import { useRecording } from '../contexts/RecordingContext.tsx';
import { Cpu, Activity, BarChart, Zap, Mic, Upload } from 'lucide-react';

interface RecorderPageProps {
	transcript: any;
	onOpenEditor: (id: string) => void;
}

export const RecorderPage: React.FC<RecorderPageProps> = ({
	transcript,
	onOpenEditor,
}) => {
	const { status, audioLevel, isProcessing, processingMessage } =
		useRecording();
	const isRecording = status === 'recording';
	const [activeTab, setActiveTab] = useState<'record' | 'upload'>('record');

	return (
		<div className="max-w-5xl mx-auto space-y-10 animate-none">
			{/* Transcription Settings */}
			<section className="flex justify-center py-4">
				<TranscriptionSettings isDisabled={isProcessing || isRecording} />
			</section>

			{/* Tab Navigation */}
			<section className="flex gap-2 border-b border-[var(--border-subtle)]">
				<button
					onClick={() => setActiveTab('record')}
					className={`flex items-center gap-2 px-4 py-3 font-bold text-sm transition-all border-b-2 ${
						activeTab === 'record'
							? 'text-[var(--accent-primary)] border-[var(--accent-primary)]'
							: 'text-[var(--text-muted)] border-transparent hover:text-[var(--text-secondary)]'
					}`}
				>
					<Mic className="w-4 h-4" />
					Record
				</button>
				<button
					onClick={() => setActiveTab('upload')}
					className={`flex items-center gap-2 px-4 py-3 font-bold text-sm transition-all border-b-2 ${
						activeTab === 'upload'
							? 'text-[var(--accent-primary)] border-[var(--accent-primary)]'
							: 'text-[var(--text-muted)] border-transparent hover:text-[var(--text-secondary)]'
					}`}
				>
					<Upload className="w-4 h-4" />
					Upload
				</button>
			</section>

			{/* Primary Control Deck */}
			<section className="grid grid-cols-1 lg:grid-cols-12 gap-px bg-[var(--border-subtle)] border border-[var(--border-subtle)]">
				<div className="lg:col-span-8 bg-[var(--bg-main)] p-12 flex flex-col items-center justify-center min-h-[400px]">
					<div className="mb-12 relative">
						{/* Static Signal Analyzer Look */}
						<div className="absolute -inset-8 border border-[var(--border-subtle)] opacity-20 pointer-events-none" />
						{activeTab === 'record' && (
							<AudioPulse isRecording={isRecording} level={audioLevel} />
						)}
					</div>
					{activeTab === 'record' && <AudioRecorder />}
					{activeTab === 'upload' && <AudioUploader />}
				</div>

				<div className="lg:col-span-4 bg-[var(--bg-sidebar)] p-8 flex flex-col">
					<div className="flex items-center gap-2 mb-8 border-b border-[var(--border-subtle)] pb-2">
						<Activity className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
						<h3 className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-[0.2em]">
							{APP_TEXT.RECORDER_PAGE.SIGNAL_MONITOR}
						</h3>
					</div>

					<div className="space-y-6">
						<div className="space-y-2">
							<div className="flex justify-between text-[9px] font-mono text-[var(--text-secondary)] uppercase">
								<span>{APP_TEXT.RECORDER_PAGE.INPUT_GAIN}</span>
								<span>{audioLevel.toFixed(1)}dB</span>
							</div>
							<div className="h-1.5 w-full bg-[var(--bg-main)] border border-[var(--border-subtle)]">
								<div
									className="h-full bg-[var(--accent-primary)]"
									style={{ width: `${Math.min(audioLevel * 10, 100)}%` }}
								/>
							</div>
						</div>

						<div className="space-y-2">
							<div className="flex justify-between text-[9px] font-mono text-[var(--text-secondary)] uppercase">
								<span>{APP_TEXT.RECORDER_PAGE.LATENCY}</span>
								<span>24.2ms</span>
							</div>
							<div className="h-1.5 w-full bg-[var(--bg-main)] border border-[var(--border-subtle)]">
								<div
									className="h-full bg-emerald-500"
									style={{ width: '12%' }}
								/>
							</div>
						</div>

						<div className="pt-10 space-y-4">
							<div className="flex items-center gap-2">
								<Zap className="w-4 h-4 text-[var(--text-secondary)]" />
								<span className="text-[9px] font-mono text-[var(--text-secondary)] uppercase">
									Stream Status:{' '}
									{isRecording
										? APP_TEXT.RECORDER.STATUS_CAPTURE
										: APP_TEXT.RECORDER.STATUS_IDLE}
								</span>
							</div>
							<div className="flex items-center gap-2">
								<Cpu className="w-4 h-4 text-[var(--text-secondary)]" />
								<span className="text-[9px] font-mono text-[var(--text-secondary)] uppercase">
									{APP_TEXT.RECORDER_PAGE.NEURAL_NODE_ACTIVE}
								</span>
							</div>
						</div>
					</div>
				</div>
			</section>

			{/* Logic Results Layer */}
			{(isProcessing || transcript) && (
				<section className="space-y-6">
					<div className="flex items-center gap-2 px-2">
						<BarChart className="w-3.5 h-3.5 text-[var(--text-secondary)]" />
						<h3 className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-[0.2em]">
							{APP_TEXT.RECORDER_PAGE.PROCESSING_STREAM}
						</h3>
					</div>

					<div className="space-y-6">
						{/* Engine Progress Indicator */}
						{isProcessing && (
							<div className="p-8 border border-[var(--border-subtle)] bg-[var(--bg-sidebar)] flex items-center gap-6">
								<div className="w-10 h-10 border border-[var(--border-subtle)] bg-[var(--bg-main)] flex items-center justify-center">
									<Activity className="w-6 h-6 text-[var(--accent-primary)]" />
								</div>
								<div>
									<p className="text-xs font-bold text-[var(--text-primary)] uppercase tracking-widest">
										{processingMessage || APP_TEXT.RECORDER.POLLING_TITLE}
									</p>
									<p className="text-[10px] font-mono text-[var(--text-secondary)] mt-1 uppercase">
										OPS_QUEUE:{' '}
										{processingMessage
											? APP_TEXT.RECORDER_PAGE.OPS_QUEUE_VERIFYING
											: APP_TEXT.RECORDER_PAGE.OPS_QUEUE_LINKING}
									</p>
								</div>
							</div>
						)}

						{/* Final Transcript Brief */}
						{transcript && (
							<div className="grid grid-cols-1 gap-6">
								<SummaryCard transcript={transcript} />

								<div className="border border-[var(--border-subtle)] bg-[var(--bg-main)]">
									<div className="px-6 py-3 border-b border-[var(--border-subtle)] bg-[var(--bg-sidebar)] flex justify-between items-center">
										<div className="flex items-center gap-2">
											<Cpu className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
											<h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--text-primary)]">
												{APP_TEXT.RECORDER.FINAL_RESULT_LABEL}
											</h2>
										</div>
										<button
											onClick={() => onOpenEditor(transcript.id)}
											className="px-4 py-1.5 bg-[var(--accent-primary)] text-white text-[10px] font-bold uppercase tracking-widest hover:opacity-90 transition-none"
										>
											{APP_TEXT.RECORDER.OPEN_EDITOR_BUTTON}
										</button>
									</div>
									<div className="p-10 text-lg leading-[1.8] text-[var(--text-primary)] whitespace-pre-wrap selection:bg-[var(--accent-primary)] selection:text-white">
										{transcript.text}
									</div>
								</div>
							</div>
						)}
					</div>
				</section>
			)}
		</div>
	);
};
