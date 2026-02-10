"""DM orchestrator — Claude API tool-use loop driving the game session."""

import json
import os
from pathlib import Path
from typing import AsyncGenerator

import anthropic

from app.orchestrator.parser import strip_markers
from app.orchestrator.tools import TOOL_SCHEMAS, ToolHandler

PROMPTS_DIR = Path(__file__).parent / "prompts"
MAX_TOOL_ROUNDS = 10


def load_system_prompt() -> str:
    """Load the DM system prompt."""
    return (PROMPTS_DIR / "dm_system.md").read_text()


def build_context_block(campaign_dir: Path) -> str:
    """Build initial context from campaign state for the system prompt."""
    parts = []

    # Campaign overview
    overview_path = campaign_dir / "campaign-overview.json"
    if overview_path.exists():
        overview = json.loads(overview_path.read_text())
        parts.append(f"Campaign: {overview.get('campaign_name', 'Unknown')}")
        pos = overview.get("player_position", {})
        if pos.get("current_location"):
            parts.append(f"Current location: {pos['current_location']}")
        parts.append(f"Time: {overview.get('time_of_day', '?')} on {overview.get('current_date', '?')}")

    # Character summary
    char_path = campaign_dir / "character.json"
    if char_path.exists():
        char = json.loads(char_path.read_text())
        parts.append(
            f"Player character: {char.get('name', '?')} — "
            f"Level {char.get('level', 1)} {char.get('race', '?')} {char.get('class', '?')}, "
            f"HP {char.get('hp', {}).get('current', '?')}/{char.get('hp', {}).get('max', '?')}"
        )

    # Session log tail
    log_path = campaign_dir / "session-log.md"
    if log_path.exists():
        lines = log_path.read_text().strip().split("\n")
        tail = lines[-20:] if len(lines) > 20 else lines
        parts.append(f"Recent session log:\n{''.join(l + chr(10) for l in tail)}")

    return "\n\n".join(parts)


class DMOrchestrator:
    """Runs the DM agent loop via Claude API with tool use."""

    def __init__(self, campaign_dir: Path, data_dir: Path):
        self.campaign_dir = campaign_dir
        self.data_dir = data_dir
        self.client = anthropic.Anthropic()
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
        self.tools = ToolHandler(campaign_dir, data_dir)
        self.system_prompt = load_system_prompt()
        self.context = build_context_block(campaign_dir)
        self.messages: list[dict] = []
        self._roll_result: dict | None = None

    def resolve_roll(self, result: dict):
        """Called by session router after the player completes a dice roll."""
        self._roll_result = result

    async def run_turn(self, player_message: str) -> AsyncGenerator[dict, None]:
        """Execute one DM turn. Yields message dicts for the WebSocket.

        Yields:
            {"type": "text", "content": "..."} — streamed narration text
            {"type": "state", "updates": {...}} — character state changes
            {"type": "roll_request", ...} — dice roll request (generator suspends until resolve_roll)
        """
        self.messages.append({"role": "user", "content": player_message})

        system = f"{self.system_prompt}\n\n## Current Campaign State\n\n{self.context}"

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=self.messages,
                tools=TOOL_SCHEMAS,
            )

            # Collect text and tool uses from this response
            assistant_content = []
            tool_results = []  # Cache results to avoid double-execution

            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                    yield {"type": "text", "content": strip_markers(block.text), "_raw": block.text}

                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

                    if block.name == "roll_dice":
                        # Yield roll request — generator suspends here
                        yield {
                            "type": "roll_request",
                            "tool_use_id": block.id,
                            "notation": block.input["notation"],
                            "reason": block.input.get("reason", ""),
                        }
                        # After __anext__() resumes us, _roll_result is set
                        result = self._roll_result
                        self._roll_result = None
                    else:
                        result = self.tools.execute(block.name, block.input)

                    # Cache for the continuation message
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })

                    if block.name in ("update_hp", "update_xp", "update_inventory", "update_gold"):
                        yield {"type": "state", "updates": result}

            # Add assistant response to history
            self.messages.append({"role": "assistant", "content": assistant_content})

            if not tool_results:
                # No tool calls — DM is done narrating
                break

            # Continue the loop with tool results
            self.messages.append({"role": "user", "content": tool_results})
