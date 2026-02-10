/** Web Audio API — four-channel audio engine with per-channel volume. */

import { useCallback, useRef } from "react";
import type { AudioMode } from "../types";

export type AudioChannel = "narrator" | "npc" | "ambient" | "sfx";

export function useAudio() {
  const ctx = useRef<AudioContext | null>(null);
  const mode = useRef<AudioMode>("full");

  // Per-channel gain nodes
  const gains = useRef<Record<AudioChannel, GainNode | null>>({
    narrator: null,
    npc: null,
    ambient: null,
    sfx: null,
  });

  // Voice channel: sequential queue
  const voiceQueue = useRef<{ data: ArrayBuffer; speaker: string }[]>([]);
  const voicePlaying = useRef(false);

  // Ambient channel: looping with crossfade
  const ambientSource = useRef<AudioBufferSourceNode | null>(null);
  const ambientFadeGain = useRef<GainNode | null>(null);

  const getContext = useCallback(() => {
    if (!ctx.current) {
      ctx.current = new AudioContext();
    }
    if (ctx.current.state === "suspended") {
      ctx.current.resume();
    }
    return ctx.current;
  }, []);

  /** Get or create a persistent gain node for a channel. */
  const getGain = useCallback(
    (channel: AudioChannel): GainNode => {
      if (!gains.current[channel]) {
        const ac = getContext();
        const gain = ac.createGain();
        gain.connect(ac.destination);
        gains.current[channel] = gain;
      }
      return gains.current[channel]!;
    },
    [getContext]
  );

  const drainVoiceQueue = useCallback(async () => {
    if (voicePlaying.current) return;
    const next = voiceQueue.current.shift();
    if (!next) return;

    voicePlaying.current = true;
    const ac = getContext();
    const channel: AudioChannel = next.speaker === "narrator" ? "narrator" : "npc";

    try {
      const buffer = await ac.decodeAudioData(next.data);
      const source = ac.createBufferSource();
      source.buffer = buffer;
      source.connect(getGain(channel));
      source.onended = () => {
        voicePlaying.current = false;
        drainVoiceQueue();
      };
      source.start();
    } catch {
      voicePlaying.current = false;
      drainVoiceQueue();
    }
  }, [getContext, getGain]);

  const playVoice = useCallback(
    async (audioData: ArrayBuffer, speaker: string = "narrator") => {
      voiceQueue.current.push({ data: audioData, speaker });
      drainVoiceQueue();
    },
    [drainVoiceQueue]
  );

  const playAmbient = useCallback(
    async (audioData: ArrayBuffer) => {
      const ac = getContext();
      const buffer = await ac.decodeAudioData(audioData);
      const masterGain = getGain("ambient");

      // Crossfade: fade out old ambient over 2s
      if (ambientSource.current && ambientFadeGain.current) {
        const oldGain = ambientFadeGain.current;
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

      // Create new ambient source with fade in — connects through crossfade gain → master gain
      const fadeGain = ac.createGain();
      fadeGain.gain.setValueAtTime(0, ac.currentTime);
      fadeGain.gain.linearRampToValueAtTime(1, ac.currentTime + 2);
      fadeGain.connect(masterGain);

      const source = ac.createBufferSource();
      source.buffer = buffer;
      source.loop = true;
      source.connect(fadeGain);
      source.start();

      ambientSource.current = source;
      ambientFadeGain.current = fadeGain;
    },
    [getContext, getGain]
  );

  const playSfx = useCallback(
    async (audioData: ArrayBuffer) => {
      const ac = getContext();
      const buffer = await ac.decodeAudioData(audioData);
      const source = ac.createBufferSource();
      source.buffer = buffer;
      source.connect(getGain("sfx"));
      source.start();
    },
    [getContext, getGain]
  );

  const setMode = useCallback(
    (newMode: AudioMode) => {
      mode.current = newMode;
      if (newMode === "off" && ambientSource.current) {
        try {
          ambientSource.current.stop();
        } catch {
          /* already stopped */
        }
        ambientSource.current = null;
        ambientFadeGain.current = null;
      }
    },
    []
  );

  /** Set volume for a specific channel (0–1). */
  const setVolume = useCallback(
    (channel: AudioChannel, value: number) => {
      const gain = getGain(channel);
      gain.gain.setValueAtTime(value, getContext().currentTime);
    },
    [getContext, getGain]
  );

  /** Stop all audio playback — voice queue, ambient, everything. */
  const stopAll = useCallback(() => {
    // Clear voice queue and stop current playback
    voiceQueue.current = [];
    voicePlaying.current = false;

    // Stop ambient
    if (ambientSource.current) {
      try {
        ambientSource.current.stop();
      } catch {
        /* already stopped */
      }
      ambientSource.current = null;
      ambientFadeGain.current = null;
    }

    // Close and reset the AudioContext
    if (ctx.current) {
      ctx.current.close();
      ctx.current = null;
      // Reset gain node refs so they're recreated fresh
      gains.current = { narrator: null, npc: null, ambient: null, sfx: null };
    }
  }, []);

  return { playVoice, playAmbient, playSfx, setMode, setVolume, stopAll, getContext };
}
