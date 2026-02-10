/** Web Audio API — three-channel audio engine. */

import { useCallback, useRef } from "react";
import type { AudioMode } from "../types";

export function useAudio() {
  const ctx = useRef<AudioContext | null>(null);
  const mode = useRef<AudioMode>("full");

  // Voice channel: sequential queue
  const voiceQueue = useRef<ArrayBuffer[]>([]);
  const voicePlaying = useRef(false);

  // Ambient channel: looping with crossfade
  const ambientSource = useRef<AudioBufferSourceNode | null>(null);
  const ambientGain = useRef<GainNode | null>(null);

  const getContext = useCallback(() => {
    if (!ctx.current) {
      ctx.current = new AudioContext();
    }
    // Resume if suspended (browser autoplay policy)
    if (ctx.current.state === "suspended") {
      ctx.current.resume();
    }
    return ctx.current;
  }, []);

  const drainVoiceQueue = useCallback(async () => {
    if (voicePlaying.current) return;
    const next = voiceQueue.current.shift();
    if (!next) return;

    voicePlaying.current = true;
    const ac = getContext();

    try {
      const buffer = await ac.decodeAudioData(next);
      const source = ac.createBufferSource();
      source.buffer = buffer;
      source.connect(ac.destination);
      source.onended = () => {
        voicePlaying.current = false;
        drainVoiceQueue();
      };
      source.start();
    } catch {
      voicePlaying.current = false;
      drainVoiceQueue();
    }
  }, [getContext]);

  const playVoice = useCallback(
    async (audioData: ArrayBuffer) => {
      voiceQueue.current.push(audioData);
      drainVoiceQueue();
    },
    [drainVoiceQueue]
  );

  const playAmbient = useCallback(
    async (audioData: ArrayBuffer) => {
      const ac = getContext();
      const buffer = await ac.decodeAudioData(audioData);

      // Crossfade: fade out old ambient over 2s
      if (ambientSource.current && ambientGain.current) {
        const oldGain = ambientGain.current;
        const oldSource = ambientSource.current;
        oldGain.gain.setValueAtTime(oldGain.gain.value, ac.currentTime);
        oldGain.gain.linearRampToValueAtTime(0, ac.currentTime + 2);
        setTimeout(() => {
          try {
            oldSource.stop();
          } catch {
            /* already stopped */
          }
        }, 2100);
      }

      // Create new ambient source with fade in
      const gain = ac.createGain();
      gain.gain.setValueAtTime(0, ac.currentTime);
      gain.gain.linearRampToValueAtTime(1, ac.currentTime + 2);
      gain.connect(ac.destination);

      const source = ac.createBufferSource();
      source.buffer = buffer;
      source.loop = true;
      source.connect(gain);
      source.start();

      ambientSource.current = source;
      ambientGain.current = gain;
    },
    [getContext]
  );

  const playSfx = useCallback(
    async (audioData: ArrayBuffer) => {
      const ac = getContext();
      const buffer = await ac.decodeAudioData(audioData);
      const source = ac.createBufferSource();
      source.buffer = buffer;
      source.connect(ac.destination);
      source.start();
    },
    [getContext]
  );

  const setMode = useCallback(
    (newMode: AudioMode) => {
      mode.current = newMode;
      // Stop ambient when switching to off
      if (newMode === "off" && ambientSource.current) {
        try {
          ambientSource.current.stop();
        } catch {
          /* already stopped */
        }
        ambientSource.current = null;
        ambientGain.current = null;
      }
    },
    []
  );

  return { playVoice, playAmbient, playSfx, setMode, getContext };
}
