import { useQuery } from '@tanstack/react-query';
import { endpoints } from '../config';

export interface BackendInfo {
	available: boolean;
	acceleration: string;
	models: string[];
}

export interface ModelInfo {
	speed: string;
	accuracy: string;
	description: string;
}

export interface TranscriptionBackendsResponse {
	backends: Record<string, BackendInfo>;
	default_backend: string;
	default_model: string;
	preloaded_models: string[];
	model_info: Record<string, ModelInfo>;
}

export const useTranscriptionBackends = () => {
	return useQuery<TranscriptionBackendsResponse>({
		queryKey: ['transcription-backends'],
		queryFn: async () => {
			const response = await fetch(endpoints.transcriptionBackends);
			if (!response.ok) {
				throw new Error('Failed to fetch transcription backends');
			}
			return response.json();
		},
		staleTime: 5 * 60 * 1000, // Cache for 5 minutes
		retry: 2,
	});
};
