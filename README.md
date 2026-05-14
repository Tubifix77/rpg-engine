# RPG Engine

An LLM-powered RPG simulator inspired by In Nomine, with a deterministic rules engine, supernatural systems, and a web UI. Play as an angel or demon in a modern city, or as a sellsword in a medieval town.

**The LLM describes. The database decides.**

Unlike chat-wrapper RPG tools, this engine resolves all mechanics in Python before the LLM writes a single word of narration. The story always matches the dice.

## Quick Start

```bash
# Requires Python 3.7+, Flask, and Ollama with gemma3:12b
ollama pull gemma3:12b
pip install requests flask

# Modern-day celestial campaign (In Nomine)
python web_ui.py --city

# Medieval fantasy campaign
python web_ui.py
```

Then open `http://localhost:5000` in your browser.

## Two Scenarios

### Harbor City (--city) — In Nomine Celestial Campaign

Play as a Malakite of War — an angel in a human vessel, investigating demonic activity in a modern city. Full supernatural systems active.

- **17 locations** across 4 districts: Downtown, Waterfront, Midtown, Eastside
- **9 NPCs**: 3 angels (surgeon, detective, ancient librarian), 2 demons (nightclub owner, information broker), 4 humans (cop, priest, bartender, nurse)
- **Songs**: 5 supernatural abilities × 3 realms each (Healing, Thunder, Shields, Motion, Tongues) — costs Essence, generates Disturbance
- **Disturbance**: use a Song and every celestial in the neighborhood might detect you
- **Dissonance**: act against your angelic nature and accumulate moral corruption — enough triggers permanent Discord flaws
- **The War**: a demon is building a Tether to Hell in a warehouse. An ancient angel watches and does nothing. A human detective is getting too close to the truth. Your move.

### Millhaven — Medieval Fantasy Campaign

A wandering sellsword in a small farming town with intertwined plot threads.

- **15 locations**: tavern, market, temple, gates, forest, bandit camp, and more
- **7 NPCs** with goals, secrets, and dispositions
- **10 world facts** (4 public, 6 secret): missing mayor, weapon smuggling, poisoned well, planned bandit raid

## How It Works

```
Player Input
  → Pass 1: LLM determines mechanical actions (structured, no prose)
  → Validator: checks entity existence, location, dead NPCs
  → Plausibility: LLM judges AUTO / CHECK / IMPOSSIBLE
  → Rules Engine: d666 dice, damage, armor, movement
  → Pass 2: LLM narrates grounded in mechanical results
Player sees narrative + mechanical truth
```

## Features

### Core Engine
- **d666 resolution**: 2d6 vs target number, 3rd d6 = check digit (degree of success). 111 = Divine Intervention, 666 = Infernal Intervention.
- **Six stats**: Strength, Agility (Corporeal) / Intelligence, Precision (Ethereal) / Will, Perception (Celestial)
- **Weapons and armor**: base damage + check digit - armor absorption, slashing/piercing/bludgeoning types
- **Morale**: NPCs flee based on Will checks when HP drops below their threshold
- **Economy**: silver currency, buy/sell with merchants
- **Encumbrance**: weight tracking against Strength-derived capacity
- **Survival**: hunger, thirst, fatigue counters with stat penalties
- **Plausibility engine**: whitelist for common actions, LLM only consulted for ambiguous cases
- **Anti-hallucination**: validator rejects invented NPCs, dead targets, impossible movement, items not in inventory

### Supernatural Systems (Harbor City)
- **Songs**: 5 Songs × 3 realms, d666 resolution, Essence cost, 13 effect handlers (heal, damage, shields, telekinesis, truth compulsion, and more)
- **Disturbance**: BFS location graph traversal, Perception-based detection with distance penalty — use Songs carelessly and every celestial nearby knows
- **Dissonance**: 7 Angel Choirs and 7 Demon Bands each with unique moral triggers. Seraphim can't lie. Mercurians can't harm humans. Calabim must destroy. Accumulates into permanent Discord flaws.
- **Forces, Essence, Vessels, Roles**: full celestial character model with cover identities and power levels

### Web UI
- Dark-themed three-panel layout: character sheet, narrative center, NPC cards
- Essence bar, Nature badge, Songs list, Dissonance counter (all hidden for mundane characters)
- Clickable exits, swipe to re-roll narration, color-coded mechanics
- NPC cards with goals, knowledge, disposition, and HP

### Two-Tier Release
- **lore_config.py**: all setting terminology in one file. Swap it to rename everything for a commercial release with zero code changes.

## Architecture

See [rpg-engine-architecture.md](rpg-engine-architecture.md) for the full design document.

## Terminal Mode

The original terminal interface is still available for Millhaven:

```bash
python game.py
```

Commands: `look`, `inventory`, `status`, `loot`, `debug`, `quit`. Anything else is a player action.

## Lineage

Built on patterns from:
- **Spine Reborn**: Validator pattern (propose → validate → commit)
- **Sovereignty**: Persistent world state integrity
- **MinionAI**: Deterministic logic over LLM decisions
- **LLM Profiler**: Know your model's strengths and weaknesses

## Legal

In Nomine is a trademark of Steve Jackson Games. This is an unofficial fan project, not affiliated with or endorsed by Steve Jackson Games. Game mechanics are not copyrightable; setting terminology is used under fair use for a free, non-commercial fan work.

## License

MIT
