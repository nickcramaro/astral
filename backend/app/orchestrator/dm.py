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
        self.client = anthropic.AsyncAnthropic()
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
            {"type": "text_delta", "content": "..."} — incremental narration text
            {"type": "text_end", "_raw": "..."} — full text block complete (triggers audio)
            {"type": "state", "updates": {...}} — character state changes
            {"type": "roll_request", ...} — dice roll request (generator suspends until resolve_roll)
        """
        self.messages.append({"role": "user", "content": player_message})

        system = f"{self.system_prompt}\n\n## Current Campaign State\n\n{self.context}"

        for _ in range(MAX_TOOL_ROUNDS):
            assistant_content = []
            pending_tools = []  # (block, ...) — processed after stream closes
            sent_len = 0  # Clean-delta tracking, reset per content block

            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=self.messages,
                tools=TOOL_SCHEMAS,
            ) as stream:
                async for event in stream:
                    if event.type == "text":
                        # Snapshot-diff: strip markers from accumulated text,
                        # hold back from any '[' that might be an incomplete marker
                        clean = strip_markers(event.snapshot)
                        last_bracket = clean.rfind('[')
                        safe_end = last_bracket if last_bracket >= sent_len else len(clean)

                        if safe_end > sent_len:
                            yield {
                                "type": "text_delta",
                                "content": clean[sent_len:safe_end],
                            }
                            sent_len = safe_end

                        # Raw delta for audio buffer (processed separately)
                        yield {"type": "_raw_delta", "content": event.text}

                    elif event.type == "content_block_stop":
                        block = event.content_block

                        if block.type == "text":
                            assistant_content.append({"type": "text", "text": block.text})
                            yield {
                                "type": "text_end",
                                "content": strip_markers(block.text),
                                "_raw": block.text,
                            }
                            sent_len = 0

                        elif block.type == "tool_use":
                            assistant_content.append({
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            })
                            pending_tools.append(block)

            # Stream closed — now process tools (safe to yield/suspend)
            tool_results = []
            for block in pending_tools:
                if block.name == "roll_dice":
                    yield {
                        "type": "roll_request",
                        "tool_use_id": block.id,
                        "notation": block.input["notation"],
                        "reason": block.input.get("reason", ""),
                    }
                    result = self._roll_result
                    self._roll_result = None
                else:
                    result = self.tools.execute(block.name, block.input)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })

                if block.name in ("update_hp", "update_xp", "update_inventory", "update_gold"):
                    yield {"type": "state", "updates": result}

            self.messages.append({"role": "assistant", "content": assistant_content})

            if not tool_results:
                break

            self.messages.append({"role": "user", "content": tool_results})
