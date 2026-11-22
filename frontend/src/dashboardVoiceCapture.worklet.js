/* global AudioWorkletProcessor, registerProcessor, sampleRate */

class DashboardVoiceCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.frameLength = Math.round(sampleRate * 0.02);
    this.frame = new Float32Array(this.frameLength);
    this.offset = 0;
    this.generation = 0;
    this.enabled = false;
    this.port.onmessage = ({ data }) => {
      this.generation = data.generation;
      this.enabled = data.enabled;
      this.offset = 0;
    };
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!this.enabled || !channel) return true;
    let read = 0;
    while (read < channel.length) {
      const count = Math.min(this.frameLength - this.offset, channel.length - read);
      this.frame.set(channel.subarray(read, read + count), this.offset);
      this.offset += count;
      read += count;
      if (this.offset === this.frameLength) {
        this.port.postMessage({ generation: this.generation, frame: this.frame }, [this.frame.buffer]);
        this.frame = new Float32Array(this.frameLength);
        this.offset = 0;
      }
    }
    return true;
  }
}

registerProcessor('dashboard-voice-capture', DashboardVoiceCapture);
