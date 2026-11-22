import workletUrl from './dashboardVoiceCapture.worklet.js?url&no-inline';

const frameMs = 20;
const preRollFrames = 280 / frameMs;
const pauseFrames = 720 / frameMs;
const maxFrames = 30_000 / frameMs;
const wavRate = 16_000;

export function encodeVoiceClip(frames: Float32Array[], sampleRate = wavRate): Blob {
  const length = frames.reduce((count, frame) => count + frame.length, 0);
  const samples = new Float32Array(length);
  let offset = 0;
  for (const frame of frames) {
    samples.set(frame, offset);
    offset += frame.length;
  }
  const count = Math.min(wavRate * 30, Math.floor(length * wavRate / sampleRate));
  const wav = new DataView(new ArrayBuffer(44 + count * 2));
  wav.setUint32(0, 0x52494646); // RIFF
  wav.setUint32(4, wav.byteLength - 8, true);
  wav.setUint32(8, 0x57415645); // WAVE
  wav.setUint32(12, 0x666d7420); // fmt
  wav.setUint32(16, 16, true);
  wav.setUint16(20, 1, true); // PCM
  wav.setUint16(22, 1, true); // mono
  wav.setUint32(24, wavRate, true);
  wav.setUint32(28, wavRate * 2, true);
  wav.setUint16(32, 2, true);
  wav.setUint16(34, 16, true);
  wav.setUint32(36, 0x64617461); // data
  wav.setUint32(40, count * 2, true);
  const ratio = sampleRate / wavRate;
  for (let index = 0; index < count; index += 1) {
    const from = Math.floor(index * ratio);
    const to = Math.max(from + 1, Math.floor((index + 1) * ratio));
    let sum = 0;
    for (let sample = from; sample < to; sample += 1) sum += samples[sample];
    const value = Math.max(-1, Math.min(1, sum / (to - from)));
    wav.setInt16(44 + 2 * index, value * (value < 0 ? 32768 : 32767), true);
  }
  return new Blob([wav.buffer], { type: 'audio/wav' });
}

export async function openVoiceCapture(signal: AbortSignal, onClip: (clip: Blob | null) => void, onLost: () => void) {
  if (!navigator.mediaDevices?.getUserMedia || !window.AudioContext) {
    throw new Error('Microphone access is unavailable in this browser.');
  }
  const context = new AudioContext();
  let stream: MediaStream | undefined;
  let node: AudioWorkletNode | undefined;
  let source: MediaStreamAudioSourceNode | undefined;
  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    stream?.getTracks().forEach(track => track.stop());
    source?.disconnect();
    if (node) {
      node.port.onmessage = null;
      node.port.close();
      node.disconnect();
    }
    if (context.state !== 'closed') void context.close().catch(() => {});
  };
  signal.addEventListener('abort', close, { once: true });
  try {
    // Start the audio context under the same user gesture that requests the microphone.
    const ready = Promise.all([context.resume(), context.audioWorklet.addModule(workletUrl)]);
    const microphone = navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    }).then(result => {
      if (closed) result.getTracks().forEach(track => track.stop());
      else {
        stream = result;
        stream.getAudioTracks().forEach(track => { track.enabled = false; });
      }
      return result;
    });
    const [input] = await Promise.all([microphone, ready]);
    signal.throwIfAborted();
    const tracks = input.getAudioTracks();
    tracks.forEach(track => track.addEventListener('ended', onLost, { once: true, signal }));
    source = context.createMediaStreamSource(input);
    const worklet = new AudioWorkletNode(context, 'dashboard-voice-capture', { numberOfOutputs: 0 });
    node = worklet;
    source.connect(worklet);
    let generation = 0;
    let enabled = false;
    let noise = 0.004;
    let preRoll: Float32Array[] = [];
    let recording: Float32Array[] | undefined;
    let onset = 0;
    let voiced = 0;
    let quiet = 0;

    function setListening(listen: boolean) {
      enabled = listen;
      preRoll = [];
      recording = undefined;
      onset = voiced = quiet = 0;
      tracks.forEach(track => { track.enabled = listen; });
      worklet.port.postMessage({ generation: ++generation, enabled });
    }

    worklet.port.onmessage = ({ data }: MessageEvent<{ generation: number; frame: Float32Array }>) => {
      if (!enabled || data.generation !== generation || signal.aborted) return;
      const { frame } = data;
      const rms = Math.sqrt(frame.reduce((sum, sample) => sum + sample * sample, 0) / frame.length);
      const speech = rms > Math.max(0.012, noise * (recording ? 2 : 3));
      if (!recording) {
        if (!speech) noise = 0.96 * noise + 0.04 * rms;
        preRoll.push(frame);
        if (preRoll.length > preRollFrames) preRoll.shift();
        onset = speech ? onset + 1 : 0;
        if (onset >= 3) {
          recording = preRoll;
          voiced = onset;
        }
        return;
      }
      recording.push(frame);
      if (speech) voiced += 1;
      quiet = speech ? 0 : quiet + 1;
      if (quiet >= pauseFrames && voiced < 7) {
        recording = undefined;
        preRoll = [];
        onset = voiced = quiet = 0;
        return;
      }
      if (recording.length >= maxFrames || quiet >= pauseFrames) {
        const frames = recording;
        const overlong = quiet < pauseFrames;
        setListening(false);
        onClip(overlong ? null : encodeVoiceClip(frames, context.sampleRate));
      }
    };
    return { setListening };
  } catch (error) {
    close();
    throw error;
  }
}
