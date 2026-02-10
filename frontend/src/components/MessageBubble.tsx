import type { ChatMessage } from "../types";

interface Props {
  message: ChatMessage;
}

const NPC_PATTERN = /^([A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*){0,2}):\s(.+)/s;

/** Render basic inline markdown (bold + italic) to React elements. */
function renderInline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*"))
      return <em key={i}>{part.slice(1, -1)}</em>;
    return part;
  });
}

export function MessageBubble({ message }: Props) {
  const { role, content } = message;

  if (role === "system") {
    return <div className="message-bubble role-system role-roll">{renderInline(content)}</div>;
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
        {renderInline(dialogue)}
      </div>
    );
  }

  return <div className="message-bubble role-dm">{renderInline(content)}</div>;
}
