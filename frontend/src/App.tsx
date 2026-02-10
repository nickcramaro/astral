import { useEffect, useMemo, useState } from "react";
import { useSession } from "./hooks/useSession";
import { useAudio } from "./hooks/useAudio";
import type { AudioChannel } from "./hooks/useAudio";
import { Chat } from "./components/Chat";
import { CharacterSheet } from "./components/CharacterSheet";
import { CampaignPicker } from "./components/CampaignPicker";
import { SettingsPanel } from "./components/SettingsPanel";
import type { AudioMode, Campaign } from "./types";
import "./App.css";

function App() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [confirmLeave, setConfirmLeave] = useState(false);
  const { playVoice, playAmbient, playSfx, setMode, setVolume, stopAll, getContext } = useAudio();

  const audioCallbacks = useMemo(
    () => ({ playVoice, playAmbient, playSfx }),
    [playVoice, playAmbient, playSfx]
  );

  const { messages, character, connected, loading, waiting, send, sendRaw } = useSession(
    selectedCampaign,
    audioCallbacks
  );

  useEffect(() => {
    fetch("http://localhost:8000/campaigns/")
      .then((res) => res.json())
      .then(setCampaigns)
      .catch(console.error);
  }, []);

  const handleModeChange = (newMode: AudioMode) => {
    setMode(newMode);
    sendRaw({ type: "set_audio_mode", mode: newMode });
  };

  const handleVolumeChange = (channel: AudioChannel, value: number) => {
    setVolume(channel, value);
  };

  const handleLeaveRequest = () => {
    setConfirmLeave(true);
  };

  const handleLeaveConfirm = () => {
    stopAll();
    setConfirmLeave(false);
    setSettingsOpen(false);
    setSelectedCampaign(null);
  };

  const handleLeaveCancel = () => {
    setConfirmLeave(false);
  };

  // Resume AudioContext on first user interaction
  const handleInteraction = () => {
    getContext();
  };

  if (!selectedCampaign) {
    return (
      <CampaignPicker
        campaigns={campaigns}
        onSelect={setSelectedCampaign}
        onImport={() => {}}
      />
    );
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-content">
          <h1 className="loading-title">Astral</h1>
          <div className="loading-orb">
            <div className="loading-orb-inner" />
          </div>
          <p className="loading-text">Summoning the Dungeon Master</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout" onClick={handleInteraction}>
      <aside className="sidebar">
        <div className="sidebar-header">
          <button className="back-btn" onClick={handleLeaveRequest}>
            &larr; Campaigns
          </button>
          <button className="settings-toggle" onClick={() => setSettingsOpen(true)}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d="M6.5 1.5L6.1 3.3C5.7 3.5 5.3 3.7 5 3.9L3.2 3.3L1.7 5.9L3.1 7.2C3 7.5 3 7.8 3 8C3 8.2 3 8.5 3.1 8.8L1.7 10.1L3.2 12.7L5 12.1C5.3 12.3 5.7 12.5 6.1 12.7L6.5 14.5H9.5L9.9 12.7C10.3 12.5 10.7 12.3 11 12.1L12.8 12.7L14.3 10.1L12.9 8.8C13 8.5 13 8.2 13 8C13 7.8 13 7.5 12.9 7.2L14.3 5.9L12.8 3.3L11 3.9C10.7 3.7 10.3 3.5 9.9 3.3L9.5 1.5H6.5Z"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinejoin="round"
              />
              <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.2" />
            </svg>
          </button>
        </div>
        <div className="sidebar-section">
          <CharacterSheet character={character} />
        </div>
      </aside>
      <main className="main-panel">
        <Chat messages={messages} onSend={send} connected={connected} waiting={waiting} />
      </main>

      <SettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onModeChange={handleModeChange}
        onVolumeChange={handleVolumeChange}
      />

      {confirmLeave && (
        <div className="modal-backdrop" onClick={handleLeaveCancel}>
          <div className="modal confirm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="confirm-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                <path d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h2 className="confirm-title">Abandon Session?</h2>
            <p className="confirm-text">
              The tale pauses here, adventurer. Your progress is safe in the chronicles, but the world will fall silent.
            </p>
            <div className="confirm-actions">
              <button className="confirm-stay" onClick={handleLeaveCancel}>
                Continue Adventure
              </button>
              <button className="confirm-leave" onClick={handleLeaveConfirm}>
                Leave Session
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
