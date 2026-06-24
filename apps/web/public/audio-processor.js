/**
 * PCM AudioWorklet processor.
 *
 * Runs at the AudioContext sample rate (16 kHz).
 * Receives 128-sample float32 blocks from the Web Audio graph, converts
 * them to Int16 PCM, accumulates into 2048-sample chunks (~128 ms at 16kHz),
 * and posts the raw ArrayBuffer to the main thread for WebSocket transmission.
 *
 * Loaded via: audioCtx.audioWorklet.addModule('/audio-processor.js')
 * Instantiated via: new AudioWorkletNode(ctx, 'pcm-processor')
 */
class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buf = new Int16Array(2048);
    this._pos = 0;
  }

  /**
   * Called by the audio graph for every 128-sample block.
   * Must return true to stay alive (return false = self-destruct).
   */
  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel) return true;

    for (let i = 0; i < channel.length; i++) {
      // Clamp float32 [-1, 1] → Int16 [-32768, 32767]
      const s = Math.max(-1.0, Math.min(1.0, channel[i]));
      this._buf[this._pos++] = s < 0 ? s * 0x8000 : s * 0x7fff;

      if (this._pos === this._buf.length) {
        // Transfer ownership (zero-copy) to the main thread
        const out = this._buf.buffer.slice(0);
        this.port.postMessage(out, [out]);
        this._buf = new Int16Array(2048);
        this._pos = 0;
      }
    }

    return true;
  }
}

registerProcessor('pcm-processor', PCMProcessor);
