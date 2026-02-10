/** Landing page — select or import a campaign. */

import type { Campaign } from "../types";

interface Props {
  campaigns: Campaign[];
  onSelect: (id: string) => void;
  onImport: () => void;
}

export function CampaignPicker({ campaigns, onSelect, onImport }: Props) {
  return (
    <div className="campaign-picker">
      <h1 className="campaign-title">Astral</h1>
      <p className="campaign-subtitle">Choose a campaign or import a new one.</p>

      <div className="campaign-divider">
        <div className="campaign-divider-diamond" />
      </div>

      <div className="campaign-list">
        {campaigns.map((c) => (
          <div key={c.id} className="campaign-card" onClick={() => onSelect(c.id)}>
            <h3>{c.name}</h3>
            {c.source && <p className="source">{c.source}</p>}
            {c.entityCounts && (
              <p className="counts">
                {c.entityCounts.npcs} NPCs, {c.entityCounts.locations} locations
              </p>
            )}
          </div>
        ))}
      </div>

      <button className="import-btn" onClick={onImport}>
        Import New Campaign
      </button>
    </div>
  );
}
