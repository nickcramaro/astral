/** Web Audio API — three-channel audio engine. */

import { useCallback, useRef } from "react";
import type { AudioMode } from "../types";

export function useAudio() {
  const ctx = useRef<AudioContext | null>(null);
  const mode = useRef<AudioMode>("full");

  const getContext = useCallback(() => {
    if (!ctx.current) {
      ctx.current = new AudioContext();
    }
    return ctx.current;
  }, []);

  const playVoice = useCallback(async (_audioData: ArrayBuffer) => {
    // TODO: Decode audio data, queue on voice channel
    // Sequential playback (narration → dialogue → narration)
    const _ac = getContext();
  }, [getContext]);

  const playAmbient = useCallback(async (_audioData: ArrayBuffer) => {
    // TODO: Decode, loop on ambient channel, crossfade
    const _ac = getContext();
  }, [getContext]);

  const playSfx = useCallback(async (_audioData: ArrayBuffer) => {
    // TODO: Decode, one-shot on SFX channel
    const _ac = getContext();
  }, [getContext]);

  const setMode = useCallback((newMode: AudioMode) => {
    mode.current = newMode;
  }, []);

  return { playVoice, playAmbient, playSfx, setMode };
}
