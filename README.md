# RPG Engine

A persistent RPG world simulator where a local LLM serves as game master, grounded by a deterministic rules engine and a rigorous world state database.

**The LLM describes. The database decides.**

Unlike chat-wrapper RPG tools (SillyTavern, KoboldAI), this engine uses a three-pass architecture where mechanics are resolved BEFORE narration, ensuring the story always matches the dice.

## How It Works

```
Player Input
  -> Pass 1: LLM determines mechanical actions (fast, no prose)
  -> Validator: checks entity existence, location, intent
  -> Plausibility Engine: LLM judges AUTO / CHECK (skill roll) / IMPOSSIBLE
  -> Rules Engine: dice rolls, damage, movement
  -> Pass 2: LLM narrates grounded in actual results (streaming)
Player sees narrative + mechanical truth
```

## Features

- **Two-pass narration**: Mechanics resolve before prose. No more "you killed him" when the dice say he dodged.
- **Bidirectional combat**: NPCs fight back. Counter-attacks when they win the contested roll, with HP tracking on both sides.
- **Plausibility engine**: LLM-based common sense filter. You can't pick up a tavern. Dragging an unwilling NPC requires a strength check.
- **Entity-component world database**: SQLite source of truth. NPCs have stats, goals, knowledge, relationships, inventory. The LLM never writes directly to the database.
- **Knowledge asymmetry**: Each NPC knows different facts. The barkeeper overheard the mayor's secret. The priest was told in confession. The player knows nothing until they find out.
- **Validator catches hallucination**: Invented NPCs rejected. Dead NPCs stay dead. Movement requires valid paths. Items must exist in inventory.
- **In Nomine-inspired mechanics**: Simple 2d6 resolution. Three realms (corporeal, ethereal, celestial). Theater of mind combat.
- **Automated test suite**: Psychopath run, plausibility stress test, and diplomacy scenario. 17 turns, 0 bugs.

## Quick Start

```bash
# Requires Python 3.7+ and Ollama with gemma3:12b
ollama pull gemma3:12b
pip install requests
python game.py
```

## The Millhaven Scenario

The included scenario drops you into a small farming town with intertwined plot threads:

- **15 locations**: tavern, market, temple, gates, forest, bandit camp, burned farm, and more
- **7 NPCs** with goals, secrets, and dispositions
- **10 world facts** (4 public, 6 secret) including a missing mayor, weapon smuggling, a poisoned well, and a planned bandit raid
- **Multiple playstyles**: Be a psychopath who kills everyone. Be a diplomat who uncovers secrets. Find redemption at the temple and become a paladin. The engine handles all of them.

## Architecture

See [rpg-engine-architecture.md](rpg-engine-architecture.md) for the full design document.

## Commands

| Command | Effect |
|---------|--------|
| `look` | See current location, exits, NPCs with HP |
| `inventory` | Check your items |
| `status` | Character sheet |
| `loot` | Take items from dead NPCs |
| `debug` | Raw scene context (what the LLM sees) |
| `quit` | Exit |

Anything else is sent to the LLM as a player action.

## Lineage

Built on patterns from:
- **Spine Reborn**: Validator pattern (propose -> validate -> commit)
- **Sovereignty**: Persistent world state integrity
- **MinionAI**: Deterministic logic over LLM decisions
- **LLM Profiler**: Know your model's strengths and weaknesses

## License

MIT
