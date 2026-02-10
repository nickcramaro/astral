import type { ChatMessage } from "../types";

interface Props {
  message: ChatMessage;
}

const NPC_PATTERN = /^([A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*){0,2}):\s(.+)/s;

export function MessageBubble({ message }: Props) {
  const { role, content } = message;

  if (role === "system") {
    return <div className="message-bubble role-system">{content}</div>;
  }

  if (role === "player") {
    return <div className="message-bubble role-player">{content}</div>;
  }

  // DM message — check for NPC speaker
  const match = content.match(NPC_PATTERN);
  if (match) {
    const [, speaker, dialogue] = match;
    return (
      <div className="message-bubble role-dm has-speaker">
        <span className="speaker-name">{speaker}</span>
        {dialogue}
      </div>
    );
  }

  return <div className="message-bubble role-dm">{content}</div>;
}
