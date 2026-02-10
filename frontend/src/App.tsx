import { useEffect, useMemo, useState } from "react";
import { useSession } from "./hooks/useSession";
import { useAudio } from "./hooks/useAudio";
import { Chat } from "./components/Chat";
import { CharacterSheet } from "./components/CharacterSheet";
import { CampaignPicker } from "./components/CampaignPicker";
import { AudioControls } from "./components/AudioControls";
import type { AudioMode, Campaign } from "./types";
import "./App.css";

function App() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<string | null>(null);
  const { playVoice, playAmbient, playSfx, setMode, getContext } = useAudio();

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
        <button className="back-btn" onClick={() => setSelectedCampaign(null)}>
          &larr; Campaigns
        </button>
        <div className="sidebar-section">
          <CharacterSheet character={character} />
        </div>
        <div className="sidebar-section">
          <AudioControls onModeChange={handleModeChange} />
        </div>
      </aside>
      <main className="main-panel">
        <Chat messages={messages} onSend={send} connected={connected} waiting={waiting} />
      </main>
    </div>
  );
}

export default App;
