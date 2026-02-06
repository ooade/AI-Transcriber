import { useState, useEffect } from 'react';
import {
	useTranscription,
	useTranscriptionTask,
	type TranscriptionResult,
} from './hooks/useTranscription.ts';
import { useRecording } from './contexts/RecordingContext.tsx';
import { InsightsView } from './components/InsightsView';
import { Shell } from './components/layout/Shell';
import { ConnectionStatusBanner } from './components/ConnectionStatusBanner';

// Pages
import { RecorderPage } from './pages/RecorderPage';
import { HistoryPage } from './pages/HistoryPage';
import { EditorPage } from './pages/EditorPage';
import { QueuesPage } from './pages/QueuesPage';

type ViewMode = 'recorder' | 'history' | 'editor' | 'insights' | 'queues';

function App() {
	const [view, setView] = useState<ViewMode>('recorder');
	const [selectedId, setSelectedId] = useState<string | null>(null);

	// State for Recorder
	const {
		status,
		setIsProcessing: setProcessingInContext,
		setProcessingMessage,
		registerOnComplete,
		transcriptionOptions,
	} = useRecording();

	const isRecording = status === 'recording';
	const [transcript, setTranscript] = useState<TranscriptionResult | null>(
		null,
	);

	// State for tracking the current background task
	const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);

	// Hook handles transcription upload
	const { uploadAndTranscribe } = useTranscription({
		onError: (error) => {
			console.error('Upload failed:', error);
		},
	});

	// Hook handles task status tracking (SSE-backed)
	const { isProcessing, task } = useTranscriptionTask(currentTaskId, {
		onSuccess: (result: TranscriptionResult) => {
			setTranscript(result);
			setCurrentTaskId(null); // Clear task once finished
		},
		onError: (error: Error) => {
			console.error('Transcription task failed:', error);
			setCurrentTaskId(null);
		},
	});

	// Sync isProcessing and message with context
	useEffect(() => {
		setProcessingInContext(isProcessing);
		if (isProcessing && task?.message) {
			setProcessingMessage(task.message);
		} else if (!isProcessing) {
			setProcessingMessage(null);
		}
	}, [
		isProcessing,
		task?.message,
		setProcessingInContext,
		setProcessingMessage,
	]);

	// Reset state on new recording
	useEffect(() => {
		if (status === 'recording') {
			setTranscript(null);
			setCurrentTaskId(null);
		}
	}, [status]);

	// Handle recording complete
	useEffect(() => {
		const handleRecordingComplete = async (audioBlob: Blob) => {
			try {
				// Upload audio file to backend
				const file = new File([audioBlob], 'recording.wav', {
					type: 'audio/wav',
				});
				const taskId = await uploadAndTranscribe({
					file,
					transcriptionOptions: {
						backend: transcriptionOptions.backend,
						modelSize: transcriptionOptions.modelSize,
						language: transcriptionOptions.language,
					},
				});
				setCurrentTaskId(taskId);
			} catch (error) {
				console.error('Failed to initiate transcription:', error);
			}
		};

		registerOnComplete(handleRecordingComplete);
	}, [registerOnComplete, uploadAndTranscribe, transcriptionOptions]);

	return (
		<div className="bg-(--bg-main)">
			<ConnectionStatusBanner />
			<Shell activeView={view} onViewChange={setView} isRecording={isRecording}>
				{view === 'recorder' && (
					<RecorderPage
						transcript={transcript}
						onOpenEditor={(id) => {
							setSelectedId(id);
							setView('editor');
						}}
					/>
				)}

				{view === 'history' && (
					<HistoryPage
						onSelectSession={(id) => {
							setSelectedId(id);
							setView('editor');
						}}
					/>
				)}

				{view === 'editor' && selectedId && (
					<EditorPage
						sessionId={selectedId}
						onBack={() => setView('history')}
					/>
				)}

				{view === 'insights' && (
					<div className="max-w-5xl mx-auto">
						<InsightsView />
					</div>
				)}

				{view === 'queues' && (
					<div className="max-w-6xl mx-auto">
						<QueuesPage />
					</div>
				)}
			</Shell>
		</div>
	);
}

export default App;
