// Default to localhost, but allow override via environment variable
export const API_BASE_URL =
	import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const endpoints = {
	health: `${API_BASE_URL}/health`,
	status: `${API_BASE_URL}/system/status`,
	insights: `${API_BASE_URL}/system/insights`,
	transcriptionBackends: `${API_BASE_URL}/system/transcription-backends`,
	history: `${API_BASE_URL}/history`,
	transcribe: `${API_BASE_URL}/transcribe`,
	task: (id: string) => `${API_BASE_URL}/tasks/${id}`,
	transcription: (id: string) => `${API_BASE_URL}/transcriptions/${id}`,
	transcriptionCorrection: (id: string) =>
		`${API_BASE_URL}/transcriptions/${id}/correct`,
	transcriptionTitle: (id: string) =>
		`${API_BASE_URL}/transcriptions/${id}/title`,
	transcriptionSummarize: (id: string) =>
		`${API_BASE_URL}/transcriptions/${id}/summarize`,
	queues: `${API_BASE_URL}/queues`,
	queueRevoke: (taskId: string) => `${API_BASE_URL}/queues/revoke/${taskId}`,
	queuePurge: `${API_BASE_URL}/queues/purge`,
	audio: (path: string) =>
		`${API_BASE_URL}/audio/${path.replace(/^temp\//, '')}`,
};
