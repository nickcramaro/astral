/** Main chat panel — streaming DM text + player input. */

import { useEffect, useRef, useState } from "react";
import type { ChatMessage, RollRequestMessage, RollResultMessage } from "../types";
import type { VoiceStatus } from "../hooks/useAudio";
import { MessageBubble } from "./MessageBubble";
import { DiceRoller } from "./DiceRoller";
import { NarrationControls } from "./NarrationControls";

interface Props {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  connected: boolean;
  waiting: boolean;
  pendingRoll: RollRequestMessage | null;
  rollResult: RollResultMessage | null;
  onRollDice: () => void;
  voiceStatus: VoiceStatus;
  onPauseVoice: () => void;
  onResumeVoice: () => void;
  onReplayVoice: () => void;
}

export function Chat({
  messages,
  onSend,
  connected,
  waiting,
  pendingRoll,
  rollResult,
  onRollDice,
  voiceStatus,
  onPauseVoice,
  onResumeVoice,
  onReplayVoice,
}: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const isRolling = pendingRoll !== null || rollResult !== null;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, waiting, pendingRoll, rollResult]);

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
        {waiting && !isRolling && (
          <div className="typing-indicator">
            <span />
            <span />
            <span />
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      {pendingRoll && (
        <DiceRoller
          notation={pendingRoll.notation}
          reason={pendingRoll.reason}
          result={rollResult}
          onRoll={onRollDice}
        />
      )}
      <div className="chat-bottom">
        <NarrationControls
          status={voiceStatus}
          onPause={onPauseVoice}
          onResume={onResumeVoice}
          onReplay={onReplayVoice}
        />
        <form onSubmit={handleSubmit} className="chat-input">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={connected ? "What do you do?" : "Connecting..."}
            disabled={!connected || waiting || isRolling}
          />
          <button type="submit" className="send-btn" disabled={!connected || waiting || isRolling}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
