/** WebSocket message types from server to client. */

export interface TextMessage {
  type: "text";
  content: string;
}

export interface AudioMessage {
  type: "audio";
  channel: "voice" | "ambient" | "sfx";
  speaker?: string;
  /** Base64-encoded audio data */
  data: string;
}

export interface StateMessage {
  type: "state";
  updates: Partial<CharacterState>;
}

export type ServerMessage = TextMessage | AudioMessage | StateMessage;

/** Player → server */
export interface PlayerMessage {
  message: string;
}

/** Character sheet state */
export interface CharacterState {
  name: string;
  race: string;
  class: string;
  level: number;
  hp: number;
  maxHp: number;
  xp: number;
  abilityScores: Record<string, number>;
  inventory: string[];
  gold: number;
}

/** Campaign summary for picker */
export interface Campaign {
  id: string;
  name: string;
  source?: string;
  entityCounts?: {
    npcs: number;
    locations: number;
    items: number;
    plots: number;
  };
  hasCharacter: boolean;
}

/** Chat message for display */
export interface ChatMessage {
  id: string;
  role: "player" | "dm" | "system";
  content: string;
  speaker?: string;
  timestamp: number;
}

/** Import progress */
export interface ImportProgress {
  stage: string;
  detail?: string;
  percent?: number;
}

/** Audio mode */
export type AudioMode = "full" | "dialogue" | "ambient" | "off";
