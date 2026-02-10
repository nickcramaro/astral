/** Sidebar character sheet — HP, inventory, abilities. */

import type { CharacterState } from "../types";

interface Props {
  character: CharacterState | null;
}

const ABILITY_ABBREV: Record<string, string> = {
  strength: "STR",
  dexterity: "DEX",
  constitution: "CON",
  intelligence: "INT",
  wisdom: "WIS",
  charisma: "CHA",
};

function hpColor(percent: number): string {
  if (percent > 60) return "#4caf50";
  if (percent > 30) return "#c9a55a";
  return "#c0392b";
}

export function CharacterSheet({ character }: Props) {
  if (!character) return <div className="character-sheet empty">No character loaded</div>;

  const hpPercent = (character.hp / character.maxHp) * 100;

  return (
    <div className="character-sheet">
      <h2>{character.name}</h2>
      <p className="character-subtitle">
        {character.race} {character.class} (Level {character.level})
      </p>

      <div className="hp-bar">
        <div
          className="hp-fill"
          style={{ width: `${hpPercent}%`, background: hpColor(hpPercent) }}
        />
        <span>
          {character.hp} / {character.maxHp} HP
        </span>
      </div>

      <div className="stat-row">
        <span>XP</span>
        <span className="stat-value">{character.xp}</span>
      </div>
      <div className="stat-row">
        <span>Gold</span>
        <span className="stat-value">{character.gold}</span>
      </div>

      <div className="section-header">Abilities</div>
      <div className="ability-grid">
        {Object.entries(character.abilityScores).map(([ability, score]) => (
          <div key={ability} className="stat-row">
            <span>{ABILITY_ABBREV[ability] ?? ability}</span>
            <span className="stat-value">{score}</span>
          </div>
        ))}
      </div>

      <div className="section-header">Inventory</div>
      <ul>
        {character.inventory.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
