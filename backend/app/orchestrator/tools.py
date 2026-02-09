"""Tool schemas and handlers for the DM orchestrator."""

import json
from pathlib import Path
from typing import Any

from app.game.dice import DiceRoller
from app.game.player_manager import PlayerManager
from app.game.npc_manager import NPCManager
from app.game.location_manager import LocationManager
from app.game.session_manager import SessionManager
from app.game.plot_manager import PlotManager
from app.game.consequence_manager import ConsequenceManager
from app.game.search import WorldSearcher


TOOL_SCHEMAS = [
    {
        "name": "roll_dice",
        "description": "Roll dice using standard notation (e.g., 1d20+5, 2d6, 2d20kh1 for advantage, 2d20kl1 for disadvantage)",
        "input_schema": {
            "type": "object",
            "properties": {
                "notation": {"type": "string", "description": "Dice notation (e.g., 1d20+5)"},
                "reason": {"type": "string", "description": "What the roll is for"},
            },
            "required": ["notation"],
        },
    },
    {
        "name": "search_world",
        "description": "Search campaign world state — NPCs, locations, plots, facts, and source material",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_character",
        "description": "Get the player character's current stats, HP, inventory, and equipment",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Character name (optional, uses active character if omitted)"},
            },
        },
    },
    {
        "name": "update_hp",
        "description": "Apply damage (negative) or healing (positive) to the player character",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Character name"},
                "amount": {"type": "integer", "description": "HP change (negative for damage, positive for healing)"},
                "reason": {"type": "string", "description": "What caused the HP change"},
            },
            "required": ["name", "amount"],
        },
    },
    {
        "name": "update_xp",
        "description": "Award XP to the player character. Auto-detects level ups.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Character name"},
                "amount": {"type": "integer", "description": "XP to award"},
                "reason": {"type": "string", "description": "What the XP is for"},
            },
            "required": ["name", "amount"],
        },
    },
    {
        "name": "update_inventory",
        "description": "Add or remove an item from the player's inventory",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Character name"},
                "action": {"type": "string", "enum": ["add", "remove"], "description": "Add or remove"},
                "item": {"type": "string", "description": "Item name"},
            },
            "required": ["name", "action", "item"],
        },
    },
    {
        "name": "update_gold",
        "description": "Add or remove gold from the player character",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Character name"},
                "amount": {"type": "integer", "description": "Gold change (negative to remove)"},
            },
            "required": ["name", "amount"],
        },
    },
    {
        "name": "get_npc",
        "description": "Look up an NPC's details, history, and tags",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "NPC name"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_npc",
        "description": "Record an event in an NPC's history",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "NPC name"},
                "event": {"type": "string", "description": "What happened"},
            },
            "required": ["name", "event"],
        },
    },
    {
        "name": "create_npc",
        "description": "Create a new NPC",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "NPC name"},
                "description": {"type": "string", "description": "NPC description"},
                "attitude": {"type": "string", "enum": ["friendly", "neutral", "hostile", "unknown"], "description": "NPC attitude toward the party"},
            },
            "required": ["name", "description", "attitude"],
        },
    },
    {
        "name": "move_party",
        "description": "Update the party's current location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "New location name"},
            },
            "required": ["location"],
        },
    },
    {
        "name": "get_location",
        "description": "Look up a location's details and connections",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Location name"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "search_plots",
        "description": "Find active quests and story threads",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (optional)"},
                "status": {"type": "string", "enum": ["active", "completed", "failed"], "description": "Filter by status"},
            },
        },
    },
    {
        "name": "update_plot",
        "description": "Record progress on a quest or plot thread",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Plot/quest name"},
                "event": {"type": "string", "description": "What progress was made"},
            },
            "required": ["name", "event"],
        },
    },
    {
        "name": "check_consequences",
        "description": "Check for pending consequences that should trigger based on current conditions",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "lookup_monster",
        "description": "Look up a monster's stat block from the D&D 5e API",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Monster name (e.g., 'goblin', 'adult-red-dragon')"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "lookup_spell",
        "description": "Look up a spell's details from the D&D 5e API",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Spell name (e.g., 'fireball', 'cure-wounds')"},
            },
            "required": ["name"],
        },
    },
]


class ToolHandler:
    """Executes tool calls from the DM orchestrator against game managers."""

    def __init__(self, campaign_dir: Path, data_dir: Path):
        self.campaign_dir = campaign_dir
        self.data_dir = data_dir
        self.dice = DiceRoller()
        self.player = PlayerManager(str(data_dir))
        self.npc = NPCManager(str(data_dir))
        self.location = LocationManager(str(data_dir))
        self.session = SessionManager(str(data_dir))
        self.plot = PlotManager(str(data_dir))
        self.consequence = ConsequenceManager(str(data_dir))
        self.searcher = WorldSearcher(str(data_dir))

    def execute(self, tool_name: str, tool_input: dict) -> dict[str, Any]:
        """Execute a tool call and return the result."""
        handler = getattr(self, f"_handle_{tool_name}", None)
        if handler is None:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return handler(tool_input)
        except Exception as e:
            return {"error": f"Tool {tool_name} failed: {str(e)}"}

    def _handle_roll_dice(self, inp: dict) -> dict:
        result = self.dice.roll(inp["notation"])
        result["reason"] = inp.get("reason", "")
        return result

    def _handle_search_world(self, inp: dict) -> dict:
        return self.searcher.search_all(inp["query"])

    def _handle_get_character(self, inp: dict) -> dict:
        name = inp.get("name")
        if name:
            player = self.player.get_player(name)
        else:
            players = self.player.list_players()
            if players:
                player = self.player.get_player(players[0])
            else:
                return {"error": "No characters found"}
        return player or {"error": "Character not found"}

    def _handle_update_hp(self, inp: dict) -> dict:
        return self.player.modify_hp(inp["name"], inp["amount"])

    def _handle_update_xp(self, inp: dict) -> dict:
        return self.player.award_xp(inp["name"], inp["amount"])

    def _handle_update_inventory(self, inp: dict) -> dict:
        return self.player.modify_inventory(inp["name"], inp["action"], inp["item"])

    def _handle_update_gold(self, inp: dict) -> dict:
        return self.player.modify_gold(inp["name"], inp["amount"])

    def _handle_get_npc(self, inp: dict) -> dict:
        result = self.npc.get_npc_status(inp["name"])
        return result or {"error": f"NPC '{inp['name']}' not found"}

    def _handle_update_npc(self, inp: dict) -> dict:
        success = self.npc.update_npc(inp["name"], inp["event"])
        return {"success": success, "npc": inp["name"], "event": inp["event"]}

    def _handle_create_npc(self, inp: dict) -> dict:
        success = self.npc.create_npc(inp["name"], inp["description"], inp["attitude"])
        return {"success": success, "npc": inp["name"]}

    def _handle_move_party(self, inp: dict) -> dict:
        return self.session.move_party(inp["location"])

    def _handle_get_location(self, inp: dict) -> dict:
        result = self.location.get_location(inp["name"])
        return result or {"error": f"Location '{inp['name']}' not found"}

    def _handle_search_plots(self, inp: dict) -> dict:
        query = inp.get("query")
        status = inp.get("status")
        if query:
            return self.plot.search_plots(query)
        return self.plot.list_plots(status=status)

    def _handle_update_plot(self, inp: dict) -> dict:
        success = self.plot.update_plot(inp["name"], inp["event"])
        return {"success": success, "plot": inp["name"]}

    def _handle_check_consequences(self, inp: dict) -> dict:
        pending = self.consequence.check_pending()
        return {"pending_consequences": pending}

    def _handle_lookup_monster(self, inp: dict) -> dict:
        import requests
        name = inp["name"].lower().replace(" ", "-")
        resp = requests.get(f"https://www.dnd5eapi.co/api/monsters/{name}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "name": data.get("name"),
                "size": data.get("size"),
                "type": data.get("type"),
                "alignment": data.get("alignment"),
                "ac": data.get("armor_class"),
                "hp": data.get("hit_points"),
                "hit_dice": data.get("hit_dice"),
                "speed": data.get("speed"),
                "stats": {
                    "str": data.get("strength"),
                    "dex": data.get("dexterity"),
                    "con": data.get("constitution"),
                    "int": data.get("intelligence"),
                    "wis": data.get("wisdom"),
                    "cha": data.get("charisma"),
                },
                "cr": data.get("challenge_rating"),
                "xp": data.get("xp"),
                "actions": [{"name": a["name"], "desc": a.get("desc", "")} for a in data.get("actions", [])],
                "special_abilities": [{"name": a["name"], "desc": a.get("desc", "")} for a in data.get("special_abilities", [])],
            }
        return {"error": f"Monster '{inp['name']}' not found"}

    def _handle_lookup_spell(self, inp: dict) -> dict:
        import requests
        name = inp["name"].lower().replace(" ", "-")
        resp = requests.get(f"https://www.dnd5eapi.co/api/spells/{name}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "name": data.get("name"),
                "level": data.get("level"),
                "school": data.get("school", {}).get("name"),
                "casting_time": data.get("casting_time"),
                "range": data.get("range"),
                "duration": data.get("duration"),
                "components": data.get("components"),
                "description": " ".join(data.get("desc", [])),
                "higher_level": " ".join(data.get("higher_level", [])),
            }
        return {"error": f"Spell '{inp['name']}' not found"}
