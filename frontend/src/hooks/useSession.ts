/** WebSocket connection for gameplay session. */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage, CharacterState, ServerMessage } from "../types";

/** Map the backend character JSON to our frontend CharacterState. */
function parseCharacter(raw: Record<string, unknown>): CharacterState {
  const hp = raw.hp as { current: number; max: number } | undefined;
  return {
    name: (raw.name as string) ?? "Unknown",
    race: (raw.race as string) ?? "",
    class: (raw.class as string) ?? "",
    level: (raw.level as number) ?? 1,
    hp: hp?.current ?? 0,
    maxHp: hp?.max ?? 0,
    xp: (raw.xp as number) ?? 0,
    abilityScores: (raw.stats as Record<string, number>) ?? {},
    inventory: (raw.equipment as string[]) ?? [],
    gold: (raw.gold as number) ?? 0,
  };
}

/** Decode base64 string to ArrayBuffer. */
function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

interface AudioCallbacks {
  playVoice: (data: ArrayBuffer) => void;
  playAmbient: (data: ArrayBuffer) => void;
  playSfx: (data: ArrayBuffer) => void;
}

export function useSession(
  campaignId: string | null,
  audio?: AudioCallbacks
) {
  const ws = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [character, setCharacter] = useState<CharacterState | null>(null);
  const [connected, setConnected] = useState(false);
  const audioRef = useRef(audio);
  audioRef.current = audio;

  useEffect(() => {
    if (!campaignId) return;

    // Reset state when switching campaigns
    setMessages([]);
    setCharacter(null);
    setConnected(false);

    const socket = new WebSocket(`ws://localhost:8000/ws/session/${campaignId}`);
    ws.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);

    socket.onmessage = (event) => {
      const msg: ServerMessage = JSON.parse(event.data);

      if (msg.type === "text") {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "dm",
            content: msg.content,
            timestamp: Date.now(),
          },
        ]);
      } else if (msg.type === "state") {
        setCharacter((prev) => {
          const updates = msg.updates as Record<string, unknown>;
          if (!prev) {
            return parseCharacter(updates);
          }
          return { ...prev, ...updates };
        });
      } else if (msg.type === "audio") {
        const ab = base64ToArrayBuffer(msg.data);
        if (msg.channel === "voice") {
          audioRef.current?.playVoice(ab);
        } else if (msg.channel === "ambient") {
          audioRef.current?.playAmbient(ab);
        } else if (msg.channel === "sfx") {
          audioRef.current?.playSfx(ab);
        }
      }
    };

    return () => socket.close();
  }, [campaignId]);

  const send = useCallback((message: string) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;

    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "player",
        content: message,
        timestamp: Date.now(),
      },
    ]);

    ws.current.send(JSON.stringify({ message }));
  }, []);

  /** Send a raw control message (not wrapped in {message: ...}). */
  const sendRaw = useCallback((data: Record<string, unknown>) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
    ws.current.send(JSON.stringify(data));
  }, []);

  return { messages, character, connected, send, sendRaw };
}
