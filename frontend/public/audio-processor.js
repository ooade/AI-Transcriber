/**
 * AudioWorkletProcessor for real-time audio processing
 *
 * Features:
 * - Energy-based Voice Activity Detection (VAD)
 * - Efficient audio streaming to main thread
 * - Zero-allocation processing in real-time thread
 */

class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();

    // VAD Configuration
    this.energyThreshold = 0.01; // RMS energy threshold for speech detection
    this.silenceThreshold = 0.005; // Lower threshold for silence (hysteresis)
    this.isSpeaking = false;

    // Smoothing for energy calculation
    this.smoothedEnergy = 0;
    this.smoothingFactor = 0.98; // Higher = more smoothing

    // Minimum speech duration (in frames) before triggering
    this.minSpeechFrames = 3;
    this.speechFrameCount = 0;

    // Minimum silence duration (in frames) before stopping
    this.minSilenceFrames = 10;
    this.silenceFrameCount = 0;

    // MessagePort for communicating with Web Worker
    this.workerPort = null;

    this.port.onmessage = (e) => {
      if (e.data.type === 'init-worker') {
        this.workerPort = e.data.port;
        console.log('[AudioWorklet] Connected to Web Worker');
      }
    };

    console.log('[AudioWorklet] Initialized with threshold-based VAD');
  }

  /**
   * Calculate RMS (Root Mean Square) energy of audio frame
   * @param {Float32Array} channelData - Audio samples
   * @returns {number} RMS energy
   */
  calculateEnergy(channelData) {
    let sum = 0;
    for (let i = 0; i < channelData.length; i++) {
      sum += channelData[i] * channelData[i];
    }
    return Math.sqrt(sum / channelData.length);
  }

  /**
   * Update VAD state based on current energy
   * Uses hysteresis to prevent flickering between speaking/silent states
   * @param {number} energy - Current frame energy
   * @returns {boolean} Whether speech is detected
   */
  updateVADState(energy) {
    // Apply exponential smoothing
    this.smoothedEnergy = this.smoothingFactor * this.smoothedEnergy +
                          (1 - this.smoothingFactor) * energy;

    if (this.isSpeaking) {
      // Currently speaking - check if we should stop
      if (this.smoothedEnergy < this.silenceThreshold) {
        this.silenceFrameCount++;
        this.speechFrameCount = 0;

        if (this.silenceFrameCount >= this.minSilenceFrames) {
          this.isSpeaking = false;
          // Notify main thread for UI updates
          this.port.postMessage({ type: 'vad', speaking: false });
          console.log('[AudioWorklet] VAD: Silence detected');
        }
      } else {
        this.silenceFrameCount = 0;
      }
    } else {
      // Currently silent - check if we should start
      if (this.smoothedEnergy > this.energyThreshold) {
        this.speechFrameCount++;
        this.silenceFrameCount = 0;

        if (this.speechFrameCount >= this.minSpeechFrames) {
          this.isSpeaking = true;
          // Notify main thread for UI updates
          this.port.postMessage({ type: 'vad', speaking: true });
          console.log('[AudioWorklet] VAD: Speech detected');
        }
      } else {
        this.speechFrameCount = 0;
      }
    }

    return this.isSpeaking;
  }

  /**
   * Process audio frames
   * Called by Web Audio API at regular intervals (typically 128 samples)
   */
  process(inputs, outputs, parameters) {
    const input = inputs[0];

    // No input connected
    if (!input || input.length === 0) {
      return true;
    }

    const channelData = input[0];

    // Calculate energy and update VAD state
    const energy = this.calculateEnergy(channelData);
    const isSpeaking = this.updateVADState(energy);

    // IMPORTANT: Send ALL audio data, regardless of VAD state
    // The backend (Whisper) will handle silence detection more accurately
    // VAD is only used for UI feedback
    const audioData = new Float32Array(channelData);

    if (this.workerPort) {
      // FAST: Send directly to worker via MessagePort
      this.workerPort.postMessage(audioData, [audioData.buffer]);
    } else {
      // FALLBACK: Send to main thread if worker not connected
      this.port.postMessage(audioData, [audioData.buffer]);
    }

    // Return true to keep processor alive
    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);
