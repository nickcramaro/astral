/** Web Audio API — four-channel audio engine with per-channel volume and voice controls. */

import { useCallback, useRef, useState } from "react";
import type { AudioMode } from "../types";

export type AudioChannel = "narrator" | "npc" | "ambient" | "sfx";
export type VoiceStatus = "idle" | "playing" | "paused";

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

  // Voice playback control
  const voiceSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const voiceBufferRef = useRef<AudioBuffer | null>(null);
  const voiceChannelRef = useRef<AudioChannel>("narrator");
  const voiceStartTimeRef = useRef(0);
  const voicePauseOffsetRef = useRef(0);
  const voiceOnEndRef = useRef<(() => void) | null>(null);

  // Turn buffers for replay
  const turnBuffersRef = useRef<{ buffer: AudioBuffer; channel: AudioChannel }[]>([]);

  // Reactive voice status for UI
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>("idle");

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

  /** Play a decoded AudioBuffer on the given channel from offset. */
  const playDecodedBuffer = useCallback(
    (buffer: AudioBuffer, channel: AudioChannel, offset: number, onEnd: () => void) => {
      const ac = getContext();
      const source = ac.createBufferSource();
      source.buffer = buffer;
      source.connect(getGain(channel));

      source.onended = () => {
        // Only chain to next if this source is still the active one.
        // If stop/pause nullified the ref, skip.
        if (voiceSourceRef.current !== source) return;
        voicePlaying.current = false;
        voiceSourceRef.current = null;
        voicePauseOffsetRef.current = 0;
        onEnd();
      };

      voiceSourceRef.current = source;
      voiceBufferRef.current = buffer;
      voiceChannelRef.current = channel;
      voiceStartTimeRef.current = ac.currentTime;
      voicePauseOffsetRef.current = offset;
      voiceOnEndRef.current = onEnd;
      voicePlaying.current = true;
      setVoiceStatus("playing");

      source.start(0, offset);
    },
    [getContext, getGain]
  );

  const drainVoiceQueue = useCallback(async () => {
    if (voicePlaying.current) return;
    const next = voiceQueue.current.shift();
    if (!next) {
      setVoiceStatus("idle");
      return;
    }

    voicePlaying.current = true;
    const ac = getContext();
    const channel: AudioChannel = next.speaker === "narrator" ? "narrator" : "npc";

    try {
      const buffer = await ac.decodeAudioData(next.data);

      // Store decoded buffer for replay
      turnBuffersRef.current.push({ buffer, channel });

      playDecodedBuffer(buffer, channel, 0, () => {
        drainVoiceQueue();
      });
    } catch {
      voicePlaying.current = false;
      drainVoiceQueue();
    }
  }, [getContext, playDecodedBuffer]);

  const playVoice = useCallback(
    async (audioData: ArrayBuffer, speaker: string = "narrator") => {
      voiceQueue.current.push({ data: audioData, speaker });
      drainVoiceQueue();
    },
    [drainVoiceQueue]
  );

  /** Stop voice playback and clear turn buffers (for new turns). */
  const stopVoice = useCallback(() => {
    voiceQueue.current = [];
    const source = voiceSourceRef.current;
    voiceSourceRef.current = null; // Nullify before stop so onended doesn't chain
    if (source) {
      try { source.stop(); } catch { /* already stopped */ }
    }
    voicePlaying.current = false;
    voicePauseOffsetRef.current = 0;
    voiceOnEndRef.current = null;
    turnBuffersRef.current = [];
    setVoiceStatus("idle");
  }, []);

  /** Pause all audio (voice, ambient, sfx) by suspending the AudioContext. */
  const pauseAll = useCallback(() => {
    if (!ctx.current || ctx.current.state !== "running") return;
    ctx.current.suspend();
    setVoiceStatus("paused");
  }, []);

  /** Resume all audio by resuming the AudioContext. */
  const resumeAll = useCallback(() => {
    if (!ctx.current || ctx.current.state !== "suspended") return;
    ctx.current.resume();
    setVoiceStatus(voicePlaying.current ? "playing" : "idle");
  }, []);

  /** Replay the entire current turn's voice from the beginning. */
  const replayVoice = useCallback(() => {
    // Stop current playback
    const source = voiceSourceRef.current;
    voiceSourceRef.current = null;
    if (source) {
      try { source.stop(); } catch { /* already stopped */ }
    }
    voiceQueue.current = [];
    voicePlaying.current = false;
    voicePauseOffsetRef.current = 0;

    const buffers = turnBuffersRef.current;
    if (buffers.length === 0) {
      setVoiceStatus("idle");
      return;
    }

    let index = 0;
    const playNext = () => {
      if (index >= buffers.length) {
        voicePlaying.current = false;
        voiceSourceRef.current = null;
        // Drain any items that arrived during replay
        drainVoiceQueue();
        return;
      }
      const { buffer: buf, channel } = buffers[index++];
      playDecodedBuffer(buf, channel, 0, playNext);
    };
    playNext();
  }, [playDecodedBuffer, drainVoiceQueue]);

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
    // Stop voice
    voiceQueue.current = [];
    const source = voiceSourceRef.current;
    voiceSourceRef.current = null;
    if (source) {
      try { source.stop(); } catch { /* already stopped */ }
    }
    voicePlaying.current = false;
    turnBuffersRef.current = [];
    setVoiceStatus("idle");

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
      gains.current = { narrator: null, npc: null, ambient: null, sfx: null };
    }
  }, []);

  /** Synthesize a short dice-clatter sound via Web Audio API. */
  const playDiceRoll = useCallback(() => {
    const ac = getContext();
    const duration = 0.3;

    // White noise burst through a bandpass filter for a "clatter" sound
    const bufferSize = Math.floor(ac.sampleRate * duration);
    const buffer = ac.createBuffer(1, bufferSize, ac.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      const env = Math.exp(-i / (bufferSize * 0.15));
      data[i] = (Math.random() * 2 - 1) * env;
    }

    const source = ac.createBufferSource();
    source.buffer = buffer;

    const filter = ac.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = 3000;
    filter.Q.value = 1.5;

    source.connect(filter);
    filter.connect(getGain("sfx"));
    source.start();
  }, [getContext, getGain]);

  return {
    playVoice,
    playAmbient,
    playSfx,
    playDiceRoll,
    stopVoice,
    pauseAll,
    resumeAll,
    replayVoice,
    voiceStatus,
    setMode,
    setVolume,
    stopAll,
    getContext,
  };
}
