/** Interactive d20 dice roller — appears when the DM requests a roll. */

import { useCallback, useEffect, useRef, useState } from "react";
import type { RollResultMessage } from "../types";

interface Props {
  notation: string;
  reason: string;
  result: RollResultMessage | null;
  onRoll: () => void;
}

type RollState = "idle" | "rolling" | "result";

/** SVG d20 — icosahedron face-on silhouette. */
function D20Icon({ number, state }: { number: string; state: RollState }) {
  const stateClass =
    state === "rolling"
      ? "dice-d20 rolling"
      : state === "result"
        ? "dice-d20 landed"
        : "dice-d20";

  return (
    <div className={stateClass}>
      <svg viewBox="0 0 100 100" width="120" height="120">
        {/* Outer d20 shape — regular icosahedron face-on outline */}
        <polygon
          points="50,2 93,27 93,73 50,98 7,73 7,27"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
        />
        {/* Inner triangle faces */}
        <line x1="50" y1="2" x2="7" y2="73" stroke="currentColor" strokeWidth="1" opacity="0.4" />
        <line x1="50" y1="2" x2="93" y2="73" stroke="currentColor" strokeWidth="1" opacity="0.4" />
        <line x1="7" y1="27" x2="93" y2="73" stroke="currentColor" strokeWidth="1" opacity="0.4" />
        <line x1="93" y1="27" x2="7" y2="73" stroke="currentColor" strokeWidth="1" opacity="0.4" />
        <line x1="50" y1="98" x2="7" y2="27" stroke="currentColor" strokeWidth="1" opacity="0.4" />
        <line x1="50" y1="98" x2="93" y2="27" stroke="currentColor" strokeWidth="1" opacity="0.4" />
      </svg>
      <span className="dice-number">{number}</span>
    </div>
  );
}

export function DiceRoller({ notation, reason, result, onRoll }: Props) {
  const [state, setState] = useState<RollState>("idle");
  const [displayNumber, setDisplayNumber] = useState("?");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isCrit = result?.natural_20;
  const isFumble = result?.natural_1;

  const handleRoll = useCallback(() => {
    if (state !== "idle") return;
    setState("rolling");
    onRoll();

    // Rapid number cycling animation
    intervalRef.current = setInterval(() => {
      setDisplayNumber(String(Math.floor(Math.random() * 20) + 1));
    }, 60);
  }, [state, onRoll]);

  // When result arrives, settle the animation
  useEffect(() => {
    if (result && state === "rolling") {
      // Let the cycling run a bit longer for suspense
      setTimeout(() => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        setDisplayNumber(String(result.total));
        setState("result");
      }, 800);
    }
  }, [result, state]);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const critClass = isCrit ? " crit" : isFumble ? " fumble" : "";

  return (
    <div className={`dice-roller${critClass}`}>
      <h3 className="dice-header">{reason || "Dice Roll"}</h3>
      <p className="dice-notation">{notation}</p>

      <button
        className="dice-click-area"
        onClick={handleRoll}
        disabled={state !== "idle"}
        aria-label="Roll dice"
      >
        <D20Icon number={displayNumber} state={state} />
        {state === "idle" && <span className="dice-prompt">Click to Roll</span>}
      </button>

      {state === "result" && result && (
        <div className="dice-result">
          <span className="dice-total">{result.total}</span>
          {isCrit && <span className="dice-crit-label">CRITICAL!</span>}
          {isFumble && <span className="dice-fumble-label">Critical Miss</span>}
        </div>
      )}
    </div>
  );
}
