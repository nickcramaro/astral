/** Audio controls — volume, mode toggle, mute. */

import { useState } from "react";
import type { AudioMode } from "../types";

interface Props {
  onModeChange: (mode: AudioMode) => void;
}

const MODES: AudioMode[] = ["full", "dialogue", "ambient", "off"];

export function AudioControls({ onModeChange }: Props) {
  const [mode, setMode] = useState<AudioMode>("full");

  const handleModeChange = (newMode: AudioMode) => {
    setMode(newMode);
    onModeChange(newMode);
  };

  return (
    <div className="audio-controls">
      <div className="mode-toggle">
        {MODES.map((m) => (
          <button
            key={m}
            className={m === mode ? "active" : ""}
            onClick={() => handleModeChange(m)}
          >
            {m}
          </button>
        ))}
      </div>
    </div>
  );
}
