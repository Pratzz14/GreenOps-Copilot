import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { components } from './api/schema';
import { encodeVoiceClip, openVoiceCapture } from './dashboardVoiceCapture';

const url = '/api/v1/dashboard/chat';
type Models = components['schemas'];
type Phase = 'idle' | 'starting' | 'listening' | 'transcribing' | 'getting-answer'
  | 'preparing' | 'speaking' | 'autoplay-blocked' | 'microphone-error' | 'too-long'
  | 'transcription-error' | 'playback-error' | 'empty-transcript';
type VoiceState = { phase: Phase; handsFree: boolean; message?: string };
type Session = {
  controller: AbortController;
  handsFree: boolean;
  phase: Phase;
  audio: HTMLAudioElement;
  audioUrl?: string;
  playback: number;
  capture?: Awaited<ReturnType<typeof openVoiceCapture>>;
  clip?: Blob;
  answer?: string;
};

const idle: VoiceState = { phase: 'idle', handsFree: false };

function releaseAudio(session: Session) {
  session.playback += 1;
  session.audio.onended = null;
  session.audio.onerror = null;
  session.audio.pause();
  session.audio.removeAttribute('src');
  session.audio.load();
  if (session.audioUrl) URL.revokeObjectURL(session.audioUrl);
  session.audioUrl = undefined;
}

async function readSpeech<T>(path: string, options: RequestInit, read: (response: Response) => Promise<T>) {
  const response = await fetch(url + path, { ...options, method: 'POST' });
  if (!response.ok) throw new Error('Speech request failed.');
  return read(response);
}

export function useDashboardVoice(send: (question: string) => Promise<Models['Reply'] | undefined>) {
  const [view, setView] = useState<VoiceState>(idle);
  const current = useRef<Session | null>(null);
  const sendLatest = useRef(send);

  useLayoutEffect(() => { sendLatest.current = send; }, [send]);

  const dispose = useCallback(() => {
    const session = current.current;
    if (!session) return;
    current.current = null;
    session.controller.abort();
    releaseAudio(session);
    session.clip = undefined;
    session.answer = undefined;
  }, []);

  useLayoutEffect(() => dispose, [dispose]);
  useEffect(() => {
    function onPageHide() {
      dispose();
      setView(idle);
    }
    window.addEventListener('pagehide', onPageHide);
    return () => window.removeEventListener('pagehide', onPageHide);
  }, [dispose]);

  function end() {
    dispose();
    setView(idle);
  }

  function owns(session: Session) { return current.current === session; }

  function transition(session: Session, phase: Phase, message?: string) {
    if (!owns(session)) return;
    session.phase = phase;
    setView({ phase, handsFree: session.handsFree, message });
  }

  function startSession(handsFree: boolean) {
    dispose();
    const session: Session = {
      controller: new AbortController(), handsFree, phase: 'starting', audio: new Audio(), playback: 0,
    };
    current.current = session;
    session.audio.preload = 'auto';
    // Reuse one element, first played under the explicit Start voice or Listen tap.
    const priming = URL.createObjectURL(encodeVoiceClip([new Float32Array(160)]));
    session.audioUrl = priming;
    session.audio.src = priming;
    void session.audio.play().catch(() => {});
    return session;
  }

  function resume(session: Session) {
    if (!owns(session)) return;
    if (!session.capture) {
      end();
      return;
    }
    releaseAudio(session);
    session.clip = undefined;
    session.answer = undefined;
    session.capture.setListening(true);
    transition(session, 'listening');
  }

  function playbackFailed(session: Session) {
    if (!owns(session)) return;
    releaseAudio(session);
    transition(session, 'playback-error');
  }

  async function play(session: Session) {
    const version = ++session.playback;
    const valid = () => owns(session) && version === session.playback;
    session.audio.onended = () => { if (valid()) resume(session); };
    session.audio.onerror = () => { if (valid()) playbackFailed(session); };
    transition(session, 'preparing');
    try {
      await session.audio.play();
      if (valid()) transition(session, 'speaking');
    } catch (error) {
      if (!valid()) return;
      if (error instanceof DOMException && error.name === 'NotAllowedError') {
        transition(session, 'autoplay-blocked');
      } else {
        playbackFailed(session);
      }
    }
  }

  async function speak(session: Session, answer: string) {
    session.capture?.setListening(false);
    session.answer = answer;
    transition(session, 'preparing');
    try {
      const speech: Models['SpeechRequest'] = { text: answer };
      const audio = await readSpeech('/speech', {
        signal: session.controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(speech),
      }, response => response.blob());
      if (!owns(session)) return;
      releaseAudio(session);
      session.audioUrl = URL.createObjectURL(audio);
      session.audio.src = session.audioUrl;
      await play(session);
    } catch {
      playbackFailed(session);
    }
  }

  async function transcribe(session: Session, clip: Blob) {
    session.clip = clip;
    transition(session, 'transcribing');
    let question: string;
    try {
      const transcript = await readSpeech<Models['Transcript']>('/transcribe', {
        signal: session.controller.signal,
        headers: { 'Content-Type': clip.type },
        body: clip,
      }, response => response.json());
      question = transcript.text.trim();
    } catch {
      transition(session, 'transcription-error');
      return;
    }
    if (!owns(session)) return;
    session.clip = undefined;
    if (!question) {
      transition(session, 'empty-transcript');
      return;
    }
    if (Array.from(question).length > 2000) {
      transition(session, 'too-long');
      return;
    }
    transition(session, 'getting-answer');
    const reply = await sendLatest.current(question);
    if (!owns(session)) return;
    if (reply) await speak(session, reply.answer);
    else resume(session);
  }

  async function start() {
    const session = startSession(true);
    transition(session, 'starting');
    function microphoneFailed(message: string) {
      if (!owns(session)) return;
      dispose();
      setView({ phase: 'microphone-error', handsFree: false, message });
    }
    try {
      session.capture = await openVoiceCapture(session.controller.signal, clip => {
        if (!owns(session)) return;
        if (clip) void transcribe(session, clip);
        else transition(session, 'too-long');
      }, () => microphoneFailed('Microphone access was interrupted.'));
      if (owns(session)) resume(session);
    } catch (error) {
      const denied = error instanceof DOMException && ['NotAllowedError', 'SecurityError'].includes(error.name);
      microphoneFailed(denied ? 'Allow microphone access to use voice.' : 'The microphone is unavailable.');
    }
  }

  function listen(answer: string) {
    const session = current.current;
    if (session && session.phase !== 'listening') return;
    void speak(session ?? startSession(false), answer);
  }

  async function runQuietly(run: () => Promise<Models['Reply'] | undefined>) {
    const session = current.current;
    if (!session || session.phase !== 'listening') {
      end();
      return run();
    }
    session.capture?.setListening(false);
    transition(session, 'getting-answer');
    const reply = await run();
    resume(session);
    return reply;
  }

  function retry() {
    const session = current.current;
    if (!session) {
      void start();
      return;
    }
    if (session.phase === 'transcription-error' && session.clip) void transcribe(session, session.clip);
    else if (session.phase === 'playback-error' && session.answer) void speak(session, session.answer);
    else if (session.phase === 'autoplay-blocked') void play(session);
    else resume(session);
  }

  function interrupt() {
    const session = current.current;
    if (session) resume(session);
  }

  const busy = ['starting', 'transcribing', 'getting-answer', 'preparing', 'speaking'].includes(view.phase);
  return { ...view, busy, start, end, listen, runQuietly, interrupt, retry };
}
