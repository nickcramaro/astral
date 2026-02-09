"""Tool schemas for the DM orchestrator — Claude API tool definitions."""


def get_tool_schemas() -> list[dict]:
    """Return Claude API tool definitions for the DM agent.

    Tools wrap the game managers: search, dice, player/npc/location updates,
    5e API lookups, voice registry, etc.
    """
    # TODO: Define tool schemas mapping to game manager methods
    return [
        {
            "name": "roll_dice",
            "description": "Roll dice using standard notation (e.g., 1d20+5, 2d6, 1d20kh1)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "notation": {"type": "string", "description": "Dice notation"},
                    "reason": {"type": "string", "description": "What the roll is for"},
                },
                "required": ["notation"],
            },
        },
        {
            "name": "search_world",
            "description": "Search campaign world state and source material",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "update_player_hp",
            "description": "Modify player HP (positive to heal, negative for damage)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "character": {"type": "string"},
                    "amount": {"type": "integer"},
                    "reason": {"type": "string"},
                },
                "required": ["character", "amount"],
            },
        },
    ]
