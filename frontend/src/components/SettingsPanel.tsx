/** Settings modal — audio mode + per-channel volume mixer. */

import { useState } from "react";
import type { AudioMode } from "../types";
import type { AudioChannel } from "../hooks/useAudio";

interface Props {
  open: boolean;
  onClose: () => void;
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

export function SettingsPanel({ open, onClose, onModeChange, onVolumeChange }: Props) {
  const [mode, setMode] = useState<AudioMode>("full");
  const [volumes, setVolumes] = useState<Record<AudioChannel, number>>({
    narrator: 100,
    npc: 100,
    ambient: 100,
    sfx: 100,
  });

  if (!open) return null;

  const handleModeChange = (newMode: AudioMode) => {
    setMode(newMode);
    onModeChange(newMode);
  };

  const handleVolume = (channel: AudioChannel, value: number) => {
    setVolumes((prev) => ({ ...prev, [channel]: value }));
    onVolumeChange(channel, value / 100);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Settings</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
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
      </div>
    </div>
  );
}
