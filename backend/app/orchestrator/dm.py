"""DM orchestrator — Claude API tool-use loop driving the game session."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_system_prompt() -> str:
    """Load the DM system prompt from prompts/dm_system.md."""
    return (PROMPTS_DIR / "dm_system.md").read_text()


async def run_dm_turn(player_message: str, campaign_dir: Path):
    """Execute one DM turn: gather context, resolve mechanics, narrate.

    Yields message dicts: {"type": "text"|"audio"|"state", ...}
    """
    # TODO: Implement Claude API streaming with tool use
    # 1. Build messages array (history + player input)
    # 2. Call Claude with tools (search, dice, player/npc updates, 5e API)
    # 3. Stream response, parsing inline markers
    # 4. For each marker segment, dispatch to audio pipeline
    # 5. Yield text chunks, audio chunks, and state updates
    yield {"type": "text", "content": f"[DM orchestrator stub] {player_message}"}
