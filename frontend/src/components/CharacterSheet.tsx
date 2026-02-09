/** Sidebar character sheet — HP, inventory, abilities. */

import type { CharacterState } from "../types";

interface Props {
  character: CharacterState | null;
}

export function CharacterSheet({ character }: Props) {
  if (!character) return <div className="character-sheet empty">No character loaded</div>;

  const hpPercent = (character.hp / character.maxHp) * 100;

  return (
    <div className="character-sheet">
      <h2>{character.name}</h2>
      <p>
        {character.race} {character.class} (Level {character.level})
      </p>

      <div className="hp-bar">
        <div className="hp-fill" style={{ width: `${hpPercent}%` }} />
        <span>
          {character.hp} / {character.maxHp} HP
        </span>
      </div>

      <div className="xp">XP: {character.xp}</div>
      <div className="gold">Gold: {character.gold}</div>

      <h3>Inventory</h3>
      <ul>
        {character.inventory.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
