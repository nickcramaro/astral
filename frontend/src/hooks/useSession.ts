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

const CACHE_KEY = "astral-opening";

/** Save opening messages to sessionStorage for instant replay on refresh. */
function saveOpeningCache(campaignId: string, msgs: ChatMessage[]) {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify({ campaignId, messages: msgs }));
  } catch {
    // sessionStorage full or unavailable — not critical
  }
}

/** Load cached opening messages if they match this campaign. */
function loadOpeningCache(campaignId: string): ChatMessage[] | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const cache = JSON.parse(raw);
    if (cache.campaignId === campaignId && cache.messages?.length > 0) {
      return cache.messages;
    }
  } catch {
    // Corrupted cache — ignore
  }
  return null;
}

export function useSession(
  campaignId: string | null,
  audio?: AudioCallbacks
) {
  const ws = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [character, setCharacter] = useState<CharacterState | null>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [waiting, setWaiting] = useState(false);
  const audioRef = useRef(audio);
  audioRef.current = audio;

  // Track whether we hydrated from frontend cache — skip duplicate WS opening messages
  const hydratedRef = useRef(false);
  const playerSentRef = useRef(false);
  const openingCountRef = useRef(0);
  const skippedRef = useRef(0);

  useEffect(() => {
    if (!campaignId) return;

    // Reset state
    setCharacter(null);
    setConnected(false);
    setWaiting(false);
    playerSentRef.current = false;
    skippedRef.current = 0;

    // Check frontend cache — show opening text instantly
    const cached = loadOpeningCache(campaignId);
    if (cached) {
      setMessages(cached);
      setLoading(false);
      hydratedRef.current = true;
      openingCountRef.current = cached.length;
    } else {
      setMessages([]);
      setLoading(true);
      hydratedRef.current = false;
      openingCountRef.current = 0;
    }

    const socket = new WebSocket(`ws://localhost:8000/ws/session/${campaignId}`);
    ws.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);

    socket.onmessage = (event) => {
      const msg: ServerMessage = JSON.parse(event.data);

      if (msg.type === "text") {
        // If hydrated from cache, skip the backend's replayed opening text messages
        if (hydratedRef.current && !playerSentRef.current) {
          skippedRef.current++;
          if (skippedRef.current >= openingCountRef.current) {
            hydratedRef.current = false;
          }
          return;
        }

        setLoading(false);
        setWaiting(false);

        const chatMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "dm",
          content: msg.content,
          timestamp: Date.now(),
        };

        setMessages((prev) => {
          const next = [...prev, chatMsg];
          // Cache opening messages (everything before first player send)
          if (!playerSentRef.current && campaignId) {
            saveOpeningCache(campaignId, next.filter((m) => m.role === "dm"));
          }
          return next;
        });
      } else if (msg.type === "state") {
        setCharacter((prev) => {
          const updates = msg.updates as Record<string, unknown>;
          if (!prev) {
            return parseCharacter(updates);
          }
          return { ...prev, ...updates };
        });
      } else if (msg.type === "audio") {
        // If hydrated from cache, skip replayed audio too (already heard it)
        if (hydratedRef.current && !playerSentRef.current) {
          return;
        }

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

    playerSentRef.current = true;
    hydratedRef.current = false;
    setWaiting(true);
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

  return { messages, character, connected, loading, waiting, send, sendRaw };
}
