/** Narration playback controls — pause/play + replay. */

import type { VoiceStatus } from "../hooks/useAudio";

interface Props {
  status: VoiceStatus;
  onPause: () => void;
  onResume: () => void;
  onReplay: () => void;
}

export function NarrationControls({ status, onPause, onResume, onReplay }: Props) {
  if (status === "idle") return null;

  return (
    <div className="narration-controls">
      {status === "playing" ? (
        <button
          className="narration-btn"
          onClick={onPause}
          title="Pause narration"
          aria-label="Pause"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <rect x="3" y="2" width="4" height="12" rx="1" />
            <rect x="9" y="2" width="4" height="12" rx="1" />
          </svg>
        </button>
      ) : (
        <button
          className="narration-btn"
          onClick={onResume}
          title="Resume narration"
          aria-label="Play"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M4 2l10 6-10 6V2z" />
          </svg>
        </button>
      )}
      <button
        className="narration-btn"
        onClick={onReplay}
        title="Replay narration"
        aria-label="Replay"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M2 8a6 6 0 1 1 1.5 4" strokeLinecap="round" />
          <path d="M2 12V8h4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </div>
  );
}
