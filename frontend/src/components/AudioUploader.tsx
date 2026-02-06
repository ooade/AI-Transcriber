import React, { useState, useRef } from 'react';
import { Upload, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { useRecording } from '../contexts/RecordingContext.tsx';
import { useTranscription } from '../hooks/useTranscription';

interface AudioUploaderProps {}

const SUPPORTED_FORMATS = [
	'audio/wav',
	'audio/mpeg',
	'audio/mp4',
	'audio/ogg',
	'audio/flac',
];
const MAX_FILE_SIZE_MB = 500;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

const AudioUploader: React.FC<AudioUploaderProps> = () => {
	const fileInputRef = useRef<HTMLInputElement>(null);
	const dropZoneRef = useRef<HTMLDivElement>(null);

	const [isDragging, setIsDragging] = useState(false);
	const [selectedFile, setSelectedFile] = useState<File | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [uploadProgress, setUploadProgress] = useState(0);

	const {
		isProcessing,
		transcriptionOptions,
		setAudioSource,
		setSourceFilename,
	} = useRecording();
	const { uploadAndTranscribe, isUploading } = useTranscription();

	const validateFile = (file: File): string | null => {
		// Check file size
		if (file.size > MAX_FILE_SIZE_BYTES) {
			return `File size exceeds ${MAX_FILE_SIZE_MB}MB limit. Your file is ${(file.size / (1024 * 1024)).toFixed(1)}MB.`;
		}

		// Check file type
		if (!SUPPORTED_FORMATS.includes(file.type)) {
			return `Unsupported file format: ${file.type}. Supported formats: WAV, MP3, M4A, OGG, FLAC.`;
		}

		return null;
	};

	const handleFileSelect = async (file: File) => {
		setError(null);

		const validationError = validateFile(file);
		if (validationError) {
			setError(validationError);
			return;
		}

		setSelectedFile(file);
		await handleUpload(file);
	};

	const handleUpload = async (file: File) => {
		try {
			setUploadProgress(0);
			setError(null);

			// Simulate progress updates (since fetch doesn't have direct progress events)
			const progressInterval = setInterval(() => {
				setUploadProgress((prev) => {
					if (prev >= 90) return prev;
					return prev + Math.random() * 30;
				});
			}, 200);

			// Track the source
			setAudioSource('uploaded');
			setSourceFilename(file.name);

			await uploadAndTranscribe({
				file,
				transcriptionOptions,
			});

			clearInterval(progressInterval);
			setUploadProgress(100);

			// Reset form after successful upload
			setTimeout(() => {
				setSelectedFile(null);
				setUploadProgress(0);
				if (fileInputRef.current) {
					fileInputRef.current.value = '';
				}
			}, 1500);
		} catch (err) {
			setError(
				err instanceof Error ? err.message : 'Failed to upload audio file',
			);
			setUploadProgress(0);
		}
	};

	const handleDragEnter = (e: React.DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		setIsDragging(true);
	};

	const handleDragLeave = (e: React.DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		setIsDragging(false);
	};

	const handleDragOver = (e: React.DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
	};

	const handleDrop = (e: React.DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		setIsDragging(false);

		const files = e.dataTransfer.files;
		if (files.length > 0) {
			handleFileSelect(files[0]);
		}
	};

	const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const files = e.currentTarget.files;
		if (files && files.length > 0) {
			handleFileSelect(files[0]);
		}
	};

	const isDisabled = isProcessing || isUploading || selectedFile !== null;

	return (
		<div className="flex flex-col items-center space-y-8 py-4">
			{/* Upload Zone */}
			<div
				ref={dropZoneRef}
				onDragEnter={handleDragEnter}
				onDragLeave={handleDragLeave}
				onDragOver={handleDragOver}
				onDrop={handleDrop}
				className={`w-full max-w-md p-8 border-2 border-dashed rounded-xl transition-all ${
					isDragging
						? 'border-[var(--accent-primary)] bg-[rgba(88,101,242,0.1)]'
						: 'border-[var(--border-subtle)] bg-[var(--bg-sidebar)]'
				}`}
			>
				<input
					ref={fileInputRef}
					type="file"
					accept={SUPPORTED_FORMATS.join(',')}
					onChange={handleFileInputChange}
					disabled={isDisabled}
					className="hidden"
				/>

				<button
					onClick={() => fileInputRef.current?.click()}
					disabled={isDisabled}
					className="w-full flex flex-col items-center gap-4 py-6 cursor-pointer transition-all hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					<div className="p-3 bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-lg">
						<Upload className="w-6 h-6 text-[var(--accent-primary)]" />
					</div>
					<div className="text-center">
						<p className="text-sm font-bold text-[var(--text-primary)]">
							Drop audio file or click to select
						</p>
						<p className="text-xs text-[var(--text-muted)] mt-1">
							{SUPPORTED_FORMATS.map((format) =>
								format.split('/')[1].toUpperCase(),
							).join(', ')}{' '}
							• Max {MAX_FILE_SIZE_MB}MB
						</p>
					</div>
				</button>
			</div>

			{/* File Info & Progress */}
			{selectedFile && (
				<div className="w-full max-w-md space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
					{/* File Info */}
					<div className="p-4 bg-[var(--bg-sidebar)] border border-[var(--border-subtle)] rounded-lg">
						<div className="flex items-start justify-between gap-3">
							<div className="flex-1 min-w-0">
								<p className="text-xs font-bold text-[var(--text-primary)] truncate">
									{selectedFile.name}
								</p>
								<p className="text-[10px] text-[var(--text-muted)] mt-1">
									{(selectedFile.size / (1024 * 1024)).toFixed(2)}MB
								</p>
							</div>
							{uploadProgress === 100 ? (
								<CheckCircle className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
							) : (
								<Loader2 className="w-5 h-5 text-[var(--accent-primary)] animate-spin flex-shrink-0 mt-0.5" />
							)}
						</div>

						{/* Progress Bar */}
						{uploadProgress > 0 && uploadProgress < 100 && (
							<div className="mt-3 h-1.5 w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] overflow-hidden">
								<div
									className="h-full bg-[var(--accent-primary)] transition-all duration-300"
									style={{ width: `${uploadProgress}%` }}
								/>
							</div>
						)}

						{uploadProgress === 100 && (
							<p className="text-[10px] text-emerald-500 mt-2 font-bold uppercase">
								Upload Complete • Transcribing...
							</p>
						)}
					</div>
				</div>
			)}

			{/* Error State */}
			{error && (
				<div className="w-full max-w-md p-4 bg-[rgba(242,63,67,0.1)] border border-[var(--accent-danger)] rounded-lg animate-in fade-in slide-in-from-top-2 duration-200 flex items-start gap-3">
					<AlertCircle className="w-5 h-5 text-[var(--accent-danger)] flex-shrink-0 mt-0.5" />
					<div className="flex-1 min-w-0">
						<p className="text-xs font-bold text-[var(--accent-danger)]">
							Upload Failed
						</p>
						<p className="text-[10px] text-[var(--text-secondary)] mt-1">
							{error}
						</p>
					</div>
					<button
						onClick={() => setError(null)}
						className="flex-shrink-0 text-[var(--accent-danger)] hover:opacity-70 transition-opacity"
					>
						<X className="w-4 h-4" />
					</button>
				</div>
			)}

			{/* Info Text */}
			{!selectedFile && !error && (
				<p className="text-[10px] text-[var(--text-muted)] text-center max-w-md">
					Your file will be transcribed using the same settings as live
					recording. You can customize backend and model size in the recorder
					settings.
				</p>
			)}
		</div>
	);
};

export default AudioUploader;
