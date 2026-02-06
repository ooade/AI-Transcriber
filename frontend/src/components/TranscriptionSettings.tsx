import React, { useState } from 'react';
import { Settings } from 'lucide-react';
import { APP_TEXT } from '../constants/text';
import { useRecording } from '../contexts/RecordingContext.tsx';
import { useTranscriptionBackends } from '../hooks/useTranscriptionBackends';

interface TranscriptionSettingsProps {
	isDisabled?: boolean;
}

const TranscriptionSettings: React.FC<TranscriptionSettingsProps> = ({
	isDisabled = false,
}) => {
	const { transcriptionOptions, setTranscriptionOptions } = useRecording();

	const [showSettings, setShowSettings] = useState(false);

	const { data: backendsData } = useTranscriptionBackends();

	// Get available backends
	const availableBackends = backendsData?.backends || {};
    // Model info no longer needed as model size is managed server-side

	const updateBackend = (backend: string) => {
		setTranscriptionOptions({ ...transcriptionOptions, backend: backend as any });
	};


	return (
		<div className="flex flex-col items-center w-full">
			{/* Settings Panel */}
			{showSettings && (
				<div className="w-full max-w-md bg-[var(--bg-sidebar)] border border-[rgba(255,255,255,0.05)] rounded-lg p-4 space-y-4 animate-in slide-in-from-top-2 fade-in duration-200 mb-6">
					<div className="flex items-center justify-between">
						<h3 className="text-sm font-bold text-white flex items-center gap-2">
							<Settings className="w-4 h-4" />
							{APP_TEXT.SETTINGS.TITLE}
						</h3>
						<button
							onClick={() => setShowSettings(false)}
							className="text-[var(--text-muted)] hover:text-white text-xs"
						>
							{APP_TEXT.SETTINGS.CLOSE}
						</button>
					</div>

					{/* Backend Selection */}
					<div className="space-y-2">
						<label className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">
							{APP_TEXT.SETTINGS.BACKEND_LABEL}
						</label>
						<p className="text-[10px] text-[var(--text-muted)] opacity-70 mb-2">
							{APP_TEXT.SETTINGS.BACKEND_HINT}
						</p>
						<div className="grid grid-cols-2 gap-2">
							{Object.entries(availableBackends).map(([name, info]) => (
								<button
									key={name}
									onClick={() => updateBackend(name)}
									disabled={!info.available || isDisabled}
									className={`p-3 rounded-lg border text-left transition-all ${
										transcriptionOptions.backend === name
											? 'bg-[var(--accent-primary)] border-[var(--accent-primary)] text-white'
											: 'bg-[var(--bg-app)] border-[rgba(255,255,255,0.05)] text-[var(--text-muted)] hover:border-[rgba(255,255,255,0.1)]'
									} ${!info.available || isDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}
									title={`${name} - ${info.acceleration} acceleration`}
								>
									<div className="text-xs font-bold">{name}</div>
									<div className="text-[10px] mt-1 opacity-80">
										{info.acceleration}
									</div>
								</button>
							))}
						</div>
					</div>
				</div>
			)}

			{/* Settings Toggle Button */}
			<button
				onClick={() => setShowSettings(!showSettings)}
				disabled={isDisabled}
				className="text-[var(--text-muted)] hover:text-white text-xs flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
			>
				<Settings className="w-4 h-4" />
				<span>
					{APP_TEXT.SETTINGS.CURRENT_BACKEND_PREFIX}{transcriptionOptions.backend}
				</span>
			</button>
		</div>
	);
};

export default TranscriptionSettings;
