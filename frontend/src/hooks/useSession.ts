/** WebSocket connection for gameplay session. */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage, CharacterState, ServerMessage } from "../types";

export function useSession(campaignId: string | null) {
  const ws = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [character, setCharacter] = useState<CharacterState | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!campaignId) return;

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
        setCharacter((prev) => (prev ? { ...prev, ...msg.updates } : null));
      }
      // TODO: Handle audio messages → forward to audio engine
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

  return { messages, character, connected, send };
}
