/**
 * WAV File Encoder
 * Converts PCM audio data to WAV format (RIFF WAVE)
 */

export interface WAVEncoderOptions {
	sampleRate?: number;
	channels?: number;
}

export class WAVEncoder {
	private sampleRate: number;
	private channels: number;

	constructor(options: WAVEncoderOptions = {}) {
		this.sampleRate = options.sampleRate || 16000;
		this.channels = options.channels || 1;
	}

	/**
	 * Encode PCM audio data to WAV format
	 * @param audioData Float32Array of audio samples
	 * @returns Blob containing WAV file
	 */
	encode(audioData: Float32Array): Blob {
		const dataLength = audioData.length;
		const frameLength = dataLength;
		const numberOfChannels = this.channels;
		const sampleRate = this.sampleRate;
		const format = 1; // 1 = PCM
		const bitDepth = 16;

		const bytesPerSample = bitDepth / 8;
		const blockAlign = numberOfChannels * bytesPerSample;

		const subChunk1Size = 16; // For PCM
		const subChunk2Size = frameLength * numberOfChannels * bytesPerSample;
		const chunkSize = 36 + subChunk2Size;

		const arrayBuffer = new ArrayBuffer(44 + subChunk2Size);
		const view = new DataView(arrayBuffer);

		const writeString = (offset: number, string: string) => {
			for (let i = 0; i < string.length; i++) {
				view.setUint8(offset + i, string.charCodeAt(i));
			}
		};

		// WAV header
		writeString(0, 'RIFF'); // ChunkID
		view.setUint32(4, chunkSize, true); // ChunkSize
		writeString(8, 'WAVE'); // Format

		// fmt  subchunk
		writeString(12, 'fmt '); // Subchunk1ID
		view.setUint32(16, subChunk1Size, true); // Subchunk1Size
		view.setUint16(20, format, true); // AudioFormat (1 = PCM)
		view.setUint16(22, numberOfChannels, true); // NumChannels
		view.setUint32(24, sampleRate, true); // SampleRate
		view.setUint32(28, sampleRate * blockAlign, true); // ByteRate
		view.setUint16(32, blockAlign, true); // BlockAlign
		view.setUint16(34, bitDepth, true); // BitsPerSample

		// data subchunk
		writeString(36, 'data'); // Subchunk2ID
		view.setUint32(40, subChunk2Size, true); // Subchunk2Size

		// Write PCM data
		let offset = 44;
		for (let i = 0; i < dataLength; i++) {
			let sample = Math.max(-1, Math.min(1, audioData[i])); // Clamp to [-1, 1]
			sample = sample < 0 ? sample * 0x8000 : sample * 0x7fff; // Convert to 16-bit
			view.setInt16(offset, sample, true);
			offset += 2;
		}

		return new Blob([arrayBuffer], { type: 'audio/wav' });
	}
}

/**
 * Capture audio from MediaStream and encode to WAV
 * Returns a Promise<Blob> with WAV data
 */
export async function mediaStreamToWAV(
	stream: MediaStream,
	options: WAVEncoderOptions = {},
): Promise<Blob> {
	const sampleRate = options.sampleRate || 16000;
	const channels = options.channels || 1;

	return new Promise((resolve, reject) => {
		const audioContext = new (
			window.AudioContext ||
			(window as unknown as Record<string, unknown>).webkitAudioContext
		)({
			sampleRate,
		});

		try {
			const source = audioContext.createMediaStreamSource(stream);
			const analyser = audioContext.createAnalyser();
			const scriptProcessor = audioContext.createScriptProcessor(
				4096,
				channels,
				channels,
			);
			const audioChunks: Float32Array[] = [];

			source.connect(scriptProcessor);
			scriptProcessor.connect(analyser);
			analyser.connect(audioContext.destination);

			scriptProcessor.onaudioprocess = (event) => {
				const audioData = event.inputBuffer.getChannelData(0);
				audioChunks.push(new Float32Array(audioData));
			};

			// Cleanup after recording stops
			const cleanup = () => {
				source.disconnect();
				scriptProcessor.disconnect();
				analyser.disconnect();

				// Concatenate all chunks
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

				// Encode to WAV
				const encoder = new WAVEncoder({ sampleRate, channels });
				const wavBlob = encoder.encode(pcmData);
				resolve(wavBlob);
			};

			// Store cleanup function for external use
			(stream as unknown as { _wavCleanup?: () => void })._wavCleanup = cleanup;
		} catch (error) {
			reject(error);
		}
	});
}
