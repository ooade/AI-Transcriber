export type RecorderStatus = 'idle' | 'initializing' | 'recording' | 'stopping';
export type AudioSource = 'recorded' | 'uploaded';

export interface TranscriptionOptions {
	backend: 'faster-whisper' | 'whisper-cpp' | 'openai' | 'google';
	modelSize: 'tiny' | 'base' | 'small' | 'medium' | 'large' | 'large-v3';
	language: string;
}
