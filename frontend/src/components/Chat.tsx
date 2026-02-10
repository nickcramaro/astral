/** Main chat panel — streaming DM text + player input. */

import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  connected: boolean;
  waiting: boolean;
}

export function Chat({ messages, onSend, connected, waiting }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, waiting]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSend(input.trim());
    setInput("");
  };

  return (
    <div className="chat">
      <div className="chat-messages">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {waiting && (
          <div className="typing-indicator">
            <span />
            <span />
            <span />
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={handleSubmit} className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={connected ? "What do you do?" : "Connecting..."}
          disabled={!connected || waiting}
        />
        <button type="submit" className="send-btn" disabled={!connected || waiting}>
          Send
        </button>
      </form>
    </div>
  );
}
