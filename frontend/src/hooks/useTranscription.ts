import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { endpoints } from '../config';
import { useServerEvents } from '../contexts/ServerEventsContext';

export interface TranscriptionResult {
	id: string;
	text: string;
	audio_url?: string;
	summary?: string;
	summary_model?: string;
}

export interface TranscriptionOptions {
	backend?: string;
	modelSize?: string;
	language?: string;
}

interface UseTranscriptionOptions {
	onSuccess?: (result: TranscriptionResult) => void;
	onError?: (error: Error) => void;
}

/**
 * Principal Hook: Handles the upload mutation and returns the task tracking ID.
 */
export const useTranscription = (options: UseTranscriptionOptions = {}) => {
	const { setSSETaskId } = useServerEvents();
	const queryClient = useQueryClient();

	const uploadMutation = useMutation({
		mutationFn: async ({
			file,
			transcriptionOptions,
		}: {
			file: File;
			transcriptionOptions?: TranscriptionOptions;
		}) => {
			const formData = new FormData();
			formData.append('file', file);
			formData.append('language', transcriptionOptions?.language || 'en');
			formData.append(
				'backend',
				transcriptionOptions?.backend || 'faster-whisper',
			);
			// Model size is now managed server-side (enforced large-v3)

			const response = await fetch(endpoints.transcribe, {
				method: 'POST',
				body: formData,
			});

			if (!response.ok) {
				throw new Error('Failed to upload audio file');
			}

			const data = await response.json();
			return data.task_id as string;
		},
		onSuccess: (taskId) => {
			// Hydrate the cache immediately as pending
			queryClient.setQueryData(['task', taskId], {
				task_id: taskId,
				status: 'PENDING',
				message: 'Starting transcription...',
			});
			setSSETaskId(taskId);
		},
		onError: (error) => {
			console.error('Upload error:', error);
			options.onError?.(error as Error);
		},
	});

	return {
		uploadAndTranscribe: uploadMutation.mutateAsync,
		isUploading: uploadMutation.isPending,
		error: uploadMutation.error,
	};
};

/**
 * Principal Hook: Watches a specific task using the Query Cache.
 * The cache is synchronized by the global SSE listener.
 */
export const useTranscriptionTask = (
	taskId: string | null,
	options: UseTranscriptionOptions = {},
) => {
	const { setSSETaskId } = useServerEvents();

	const query = useQuery({
		queryKey: ['task', taskId],
		queryFn: async () => {
			if (!taskId) return null;
			const response = await fetch(endpoints.task(taskId));
			if (!response.ok) throw new Error('Failed to fetch task status');
			return response.json();
		},
		enabled: !!taskId,
		staleTime: Infinity, // Rely on SSE for updates
	});

	// Effect to trigger onSuccess/onError when task finishes
	useEffect(() => {
		const data = query.data as any;
		if (data?.status === 'SUCCESS' && data.result) {
			// If we don't have the full transcription details yet
			if (!data.result.text && data.result.id) {
				fetch(endpoints.transcription(data.result.id))
					.then((res) => res.json())
					.then((fullResult) => {
						options.onSuccess?.(fullResult);
						setSSETaskId(null);
					});
			} else {
				options.onSuccess?.(data.result);
				setSSETaskId(null);
			}
		} else if (data?.status === 'FAILURE') {
			options.onError?.(new Error(data.error || 'Transcription failed'));
			setSSETaskId(null);
		}
	}, [query.data, options, setSSETaskId]);

	return {
		task: query.data,
		isLoading: query.isLoading,
		isProcessing:
			!!taskId &&
			query.data?.status !== 'SUCCESS' &&
			query.data?.status !== 'FAILURE',
		error: query.error,
	};
};
