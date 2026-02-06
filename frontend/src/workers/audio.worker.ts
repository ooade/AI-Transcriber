/*
 * Audio Processing Web Worker
 * Handles PCM encoding off the main thread.
 *
 * Note: RNNoise noise suppression was removed as it was distorting audio
 * and reducing transcription accuracy. The threshold-based VAD in the
 * AudioWorklet provides sufficient noise gating.
 */

self.onmessage = (e: MessageEvent) => {
  const { type, port } = e.data;

  if (type === 'init') {
    initPort(port);
  }
};

let audioPort: MessagePort | null = null;

function initPort(port: MessagePort) {
  audioPort = port;

  audioPort.onmessage = (e: MessageEvent) => {
    // Receive Float32Array from AudioWorklet (-1.0 to 1.0)
    const audioData = e.data;

    // Convert to Int16 PCM
    const pcmData = convertFloat32ToInt16(audioData);

    // Send processed data to main thread
    // @ts-ignore
    self.postMessage({ type: 'audio', data: pcmData }, [pcmData]);
  };

  console.log('[AudioWorker] Initialized and connected to AudioWorklet');
}

function convertFloat32ToInt16(float32Array: Float32Array): ArrayBuffer {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);

  for (let i = 0; i < float32Array.length; i++) {
    // Standard conversion for -1..1 input
    let s = Math.max(-1, Math.min(1, float32Array[i]));
    s = s < 0 ? s * 0x8000 : s * 0x7FFF;
    view.setInt16(i * 2, s, true);
  }

  return buffer;
}
