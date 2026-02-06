import React, {
	createContext,
	useState,
	useRef,
	useEffect,
	useCallback,
	useContext,
} from 'react';
import type {
	RecorderStatus,
	AudioSource,
	TranscriptionOptions,
} from './recordingTypes';

interface RecordingContextType {
	status: RecorderStatus;
	duration: number;
	audioLevel: number;
	startRecording: () => Promise<void>;
	stopRecording: () => void;
	isProcessing: boolean;
	setIsProcessing: (loading: boolean) => void;
	processingMessage: string | null;
	setProcessingMessage: (message: string | null) => void;
	registerOnComplete: (callback: (blob: Blob) => void) => void;
	transcriptionOptions: TranscriptionOptions;
	setTranscriptionOptions: (options: TranscriptionOptions) => void;
	audioSource: AudioSource | null;
	setAudioSource: (source: AudioSource | null) => void;
	sourceFilename: string | null;
	setSourceFilename: (filename: string | null) => void;
}

const RecordingContext = createContext<RecordingContextType | undefined>(
	undefined,
);

export const RecordingProvider: React.FC<{ children: React.ReactNode }> = ({
	children,
}) => {
	const [status, setStatus] = useState<RecorderStatus>('idle');
	const [duration, setDuration] = useState<number>(0);
	const [audioLevel, setAudioLevel] = useState(0);
	const [isProcessing, setIsProcessing] = useState(false);
	const [processingMessage, setProcessingMessage] = useState<string | null>(
		null,
	);
	const [audioSource, setAudioSource] = useState<AudioSource | null>(null);
	const [sourceFilename, setSourceFilename] = useState<string | null>(null);

	// Load transcription options from localStorage or use defaults
	const [transcriptionOptions, setTranscriptionOptions] =
		useState<TranscriptionOptions>(() => {
			const stored = localStorage.getItem('transcriptionOptions');
			if (stored) {
				try {
					return JSON.parse(stored);
				} catch {
					// Fall through to defaults if parse fails
				}
			}
			return {
				backend: 'faster-whisper',
				modelSize: 'large-v3',
				language: 'en',
			};
		});

	const mediaRecorderRef = useRef<MediaRecorder | null>(null);
	const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
	const onCompleteCallbackRef = useRef<((blob: Blob) => void) | null>(null);

	// AudioContext refs for VAD/Visualization
	const audioContextRef = useRef<AudioContext | null>(null);
	const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
	const analyserRef = useRef<AnalyserNode | null>(null);
	const animationFrameRef = useRef<number | null>(null);
	const workletNodeRef = useRef<AudioWorkletNode | null>(null);

	const cleanup = useCallback(() => {
		if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
		if (animationFrameRef.current)
			cancelAnimationFrame(animationFrameRef.current);

		if (analyserRef.current) {
			analyserRef.current.disconnect();
			analyserRef.current = null;
		}
		if (workletNodeRef.current) {
			workletNodeRef.current.disconnect();
			workletNodeRef.current = null;
		}
		if (sourceRef.current) {
			sourceRef.current.disconnect();
			sourceRef.current = null;
		}
		if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
			audioContextRef.current.close();
		}
		audioContextRef.current = null;
		setAudioLevel(0);
	}, []);

	useEffect(() => {
		return () => cleanup();
	}, [cleanup]);

	// Persist transcription options to localStorage whenever they change
	useEffect(() => {
		localStorage.setItem(
			'transcriptionOptions',
			JSON.stringify(transcriptionOptions),
		);
	}, [transcriptionOptions]);

	const registerOnComplete = useCallback((callback: (blob: Blob) => void) => {
		onCompleteCallbackRef.current = callback;
	}, []);

	const startRecording = async () => {
		setStatus('initializing');
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

			// Setup AudioContext for both capture and visualization
			const AudioContextClass =
				window.AudioContext ||
				(window as unknown as Record<string, unknown>).webkitAudioContext;
			const audioContext = new AudioContextClass({
				sampleRate: 16000,
			});
			audioContextRef.current = audioContext;

			await audioContext.audioWorklet.addModule('/audio-processor.js');

			const source = audioContext.createMediaStreamSource(stream);
			sourceRef.current = source;

			// Create ScriptProcessor for audio capture to PCM
			// Note: ScriptProcessor is deprecated but widely supported and works reliably for this use case
			const scriptProcessor = audioContext.createScriptProcessor(
				4096, // buffer size
				1, // input channels
				1, // output channels
			);

			// Collect PCM data
			const audioChunks: Float32Array[] = [];
			scriptProcessor.onaudioprocess = (event) => {
				const audioData = event.inputBuffer.getChannelData(0);
				audioChunks.push(new Float32Array(audioData));
			};

			source.connect(scriptProcessor);
			scriptProcessor.connect(audioContext.destination);

			// Setup visualization (analyser)
			const analyser = audioContext.createAnalyser();
			analyser.fftSize = 256;
			source.connect(analyser);
			analyserRef.current = analyser;

			const bufferLength = analyser.frequencyBinCount;
			const dataArray = new Uint8Array(bufferLength);

			const updateLevel = () => {
				analyser.getByteFrequencyData(dataArray);
				let sum = 0;
				for (let i = 0; i < bufferLength; i++) {
					sum += dataArray[i];
				}
				const average = sum / bufferLength;
				const level = Math.min(1, (average / 128) * 1.5);
				setAudioLevel(level);
				animationFrameRef.current = requestAnimationFrame(updateLevel);
			};
			updateLevel();

			// Setup AudioWorklet for additional processing
			const workletNode = new AudioWorkletNode(audioContext, 'audio-processor');
			workletNodeRef.current = workletNode;
			source.connect(workletNode);
			workletNode.connect(audioContext.destination);

			// Store media recorder ref with stop handler
			mediaRecorderRef.current = {
				stop: async () => {
					// Disconnect nodes
					source.disconnect();
					scriptProcessor.disconnect();
					analyser.disconnect();
					if (workletNode) {
						workletNode.disconnect();
					}

					// Stop stream
					stream.getTracks().forEach((track) => track.stop());

					// Concatenate all PCM chunks into single Float32Array
					const totalLength = audioChunks.reduce(
						(acc, chunk) => acc + chunk.length,
						0,
					);
					const pcmData = new Float32Array(totalLength);
					let offset = 0;
					for (const chunk of audioChunks) {
						pcmData.set(chunk, offset);
						offset += chunk.length;
					}

					// Encode PCM to WAV format
					const { WAVEncoder } = await import('../utils/wav-encoder');
					const encoder = new WAVEncoder({
						sampleRate: 16000,
						channels: 1,
					});
					const wavBlob = encoder.encode(pcmData);

					cleanup();

					setAudioSource('recorded');
					setSourceFilename('recording.wav');

					if (onCompleteCallbackRef.current) {
						onCompleteCallbackRef.current(wavBlob);
					}

					setStatus('idle');
				},
			} as unknown as MediaRecorder;

			setStatus('recording');
			setDuration(0);
			timerIntervalRef.current = setInterval(() => {
				setDuration((prev) => prev + 1);
			}, 1000);
		} catch (error) {
			console.error('Error accessing microphone:', error);
			setStatus('idle');
			throw error;
		}
	};

	const stopRecording = () => {
		if (!mediaRecorderRef.current || status !== 'recording') return;
		setStatus('stopping');
		mediaRecorderRef.current.stop();
	};

	return (
		<RecordingContext.Provider
			value={{
				status,
				duration,
				audioLevel,
				startRecording,
				stopRecording,
				isProcessing,
				setIsProcessing,
				processingMessage,
				setProcessingMessage,
				registerOnComplete,
				transcriptionOptions,
				setTranscriptionOptions,
				audioSource,
				setAudioSource,
				sourceFilename,
				setSourceFilename,
			}}
		>
			{children}
		</RecordingContext.Provider>
	);
};

export const useRecording = () => {
	const context = useContext(RecordingContext);
	if (context === undefined) {
		throw new Error('useRecording must be used within a RecordingProvider');
	}
	return context;
};
