/** Settings panel — audio mode + per-channel volume mixer. */

import { useState } from "react";
import type { AudioMode } from "../types";
import type { AudioChannel } from "../hooks/useAudio";

interface Props {
  onModeChange: (mode: AudioMode) => void;
  onVolumeChange: (channel: AudioChannel, value: number) => void;
}

const MODES: AudioMode[] = ["full", "dialogue", "ambient", "off"];

const CHANNELS: { key: AudioChannel; label: string }[] = [
  { key: "narrator", label: "Narrator" },
  { key: "npc", label: "NPC Voices" },
  { key: "ambient", label: "Ambient" },
  { key: "sfx", label: "Effects" },
];

export function SettingsPanel({ onModeChange, onVolumeChange }: Props) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<AudioMode>("full");
  const [volumes, setVolumes] = useState<Record<AudioChannel, number>>({
    narrator: 100,
    npc: 100,
    ambient: 100,
    sfx: 100,
  });

  const handleModeChange = (newMode: AudioMode) => {
    setMode(newMode);
    onModeChange(newMode);
  };

  const handleVolume = (channel: AudioChannel, value: number) => {
    setVolumes((prev) => ({ ...prev, [channel]: value }));
    onVolumeChange(channel, value / 100);
  };

  return (
    <div className="settings-panel">
      <button className="settings-toggle" onClick={() => setOpen(!open)}>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M6.5 1.5L6.1 3.3C5.7 3.5 5.3 3.7 5 3.9L3.2 3.3L1.7 5.9L3.1 7.2C3 7.5 3 7.8 3 8C3 8.2 3 8.5 3.1 8.8L1.7 10.1L3.2 12.7L5 12.1C5.3 12.3 5.7 12.5 6.1 12.7L6.5 14.5H9.5L9.9 12.7C10.3 12.5 10.7 12.3 11 12.1L12.8 12.7L14.3 10.1L12.9 8.8C13 8.5 13 8.2 13 8C13 7.8 13 7.5 12.9 7.2L14.3 5.9L12.8 3.3L11 3.9C10.7 3.7 10.3 3.5 9.9 3.3L9.5 1.5H6.5Z"
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinejoin="round"
          />
          <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.2" />
        </svg>
        Settings
      </button>

      {open && (
        <div className="settings-content">
          <div className="settings-section">
            <div className="settings-label">Audio Mode</div>
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

          <div className="settings-section">
            <div className="settings-label">Mixer</div>
            <div className="mixer">
              {CHANNELS.map(({ key, label }) => (
                <div key={key} className="mixer-channel">
                  <span className="mixer-label">{label}</span>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={volumes[key]}
                    onChange={(e) => handleVolume(key, Number(e.target.value))}
                    className="mixer-slider"
                  />
                  <span className="mixer-value">{volumes[key]}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
