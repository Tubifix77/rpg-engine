# RPG World Engine -- Architecture Document

> **Status:** Design phase
> **Author:** Tue Boas + Claude
> **Date:** 2026-05-06

---

## 1. What This Is

A persistent RPG world simulator where a local LLM serves as game master/narrator, grounded by a deterministic rules engine and a rigorous world state database.

The LLM handles what it is good at: narrative, dialogue, improvisation. The database and rules engine handle what LLMs are bad at: consistency, memory, mechanical resolution.

**Design philosophy:** The world database is the core of the project. Everything else reads from and writes to the database. The LLM is never the source of truth for any fact about the world.

**Lineage:** Spine Reborn (validator), Sovereignty (persistent state), MinionAI (deterministic > LLM), LLM Profiler (model awareness).

---

## 2. Core Principle: Propose, Validate, Commit

No component writes directly to the world database. All changes follow:

1. **Propose** -- LLM narrates and emits a structured action block
2. **Validate** -- Rules engine checks against world state and constraints
3. **Commit** -- Valid changes applied atomically to the database

The LLM is a creative advisor. The database is the law.

---

## 3. System Architecture (Pipeline)

```
PLAYER INPUT (text action)
       |
       v
SCENE ASSEMBLER --- reads World DB
       |            builds LLM context:
       |            - current scene
       |            - player character sheet
       |            - present NPCs + dispositions
       |            - active items in scene
       |            - recent history (last N turns)
       |            - time/weather
       |
       v
LLM NARRATOR (gemma3:12b via Ollama)
       |  produces: [NARRATIVE] + [ACTIONS]
       |
       v
ACTION PARSER
       |  extracts structured changes:
       |  dice rolls, stat changes, item
       |  transfers, NPC changes, movement
       |
       v
RULES ENGINE (pure Python, no LLM)
       |  resolves dice, damage, movement
       |
       v
VALIDATOR
       |  checks against world state:
       |  entity exists? alive? at location?
       |  has item? knows fact? physically
       |  possible?
       |  ON FAIL: reject, re-prompt LLM
       |
       v
WORLD DATABASE (SQLite)
       |  atomic commit
       |
       v
RESPONSE COMPOSER
       |  narrative + mechanical results
       |  (dice outcomes, damage, items)
       |
       v
PLAYER SEES RESULT
```

---

## 4. World Database Schema (SQLite)

Entity-component system. Every world object is an entity with typed component tables.

### 4.1 Entities

```sql
CREATE TABLE entities (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    destroyed_at TEXT,
    notes       TEXT
);
```

- type: 'npc', 'player', 'location', 'item', 'faction', 'event'
- id: uuid string
- destroyed_at: null if still exists

### 4.2 Physical State

```sql
CREATE TABLE comp_physical (
    entity_id       TEXT PRIMARY KEY REFERENCES entities(id),
    hp_current      INTEGER NOT NULL,
    hp_max          INTEGER NOT NULL,
    location_id     TEXT REFERENCES entities(id),
    conditions      TEXT,
    is_alive        INTEGER NOT NULL DEFAULT 1
);
```

- conditions: JSON array e.g. ["poisoned", "bound"]

### 4.3 Stats

```sql
CREATE TABLE comp_stats (
    entity_id   TEXT PRIMARY KEY REFERENCES entities(id),
    corporeal   INTEGER NOT NULL DEFAULT 3,
    ethereal    INTEGER NOT NULL DEFAULT 3,
    celestial   INTEGER NOT NULL DEFAULT 3,
    skills      TEXT NOT NULL DEFAULT '{}'
);
```

- Three realms (In Nomine style)
- Skills as JSON: {"fighting": 2, "lying": 3}

### 4.4 Inventory

```sql
CREATE TABLE comp_inventory (
    item_id     TEXT REFERENCES entities(id),
    holder_id   TEXT REFERENCES entities(id),
    equipped    INTEGER NOT NULL DEFAULT 0,
    quantity    INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (item_id, holder_id)
);
```

### 4.5 Locations

```sql
CREATE TABLE comp_location (
    entity_id       TEXT PRIMARY KEY REFERENCES entities(id),
    parent_id       TEXT REFERENCES entities(id),
    description     TEXT,
    current_state   TEXT,
    connections     TEXT,
    is_accessible   INTEGER NOT NULL DEFAULT 1
);
```

- parent_id: region/building containment
- connections: JSON e.g. {"north": "loc_market", "door": "loc_cellar"}

### 4.6 Relationships

```sql
CREATE TABLE comp_relationships (
    entity_a    TEXT REFERENCES entities(id),
    entity_b    TEXT REFERENCES entities(id),
    rel_type    TEXT NOT NULL,
    value       INTEGER,
    details     TEXT,
    PRIMARY KEY (entity_a, entity_b, rel_type)
);
```

- rel_type: 'disposition', 'faction_member', 'family', 'rival', 'employer'
- value: -100 to +100 for disposition

### 4.7 Knowledge (Critical for Consistency)

```sql
CREATE TABLE world_facts (
    fact_id     TEXT PRIMARY KEY,
    category    TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    public      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE comp_knowledge (
    entity_id   TEXT REFERENCES entities(id),
    fact_id     TEXT REFERENCES world_facts(fact_id),
    learned_at  TEXT NOT NULL,
    source      TEXT,
    PRIMARY KEY (entity_id, fact_id)
);
```

- category: 'event', 'secret', 'location', 'identity'
- source: 'witnessed', 'told_by:npc_baker', 'rumor'
- public: 1 = common knowledge, everyone knows

### 4.8 Goals (NPC Agency)

```sql
CREATE TABLE comp_goals (
    id          TEXT PRIMARY KEY,
    entity_id   TEXT REFERENCES entities(id),
    description TEXT NOT NULL,
    priority    INTEGER NOT NULL DEFAULT 5,
    status      TEXT NOT NULL DEFAULT 'active',
    deadline    TEXT,
    blockers    TEXT
);
```

- status: 'active', 'completed', 'failed', 'abandoned'
- blockers: JSON e.g. ["needs_key", "player_has_ring"]

### 4.9 Time and History

```sql
CREATE TABLE world_clock (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    current_time TEXT NOT NULL,
    season      TEXT,
    weather     TEXT
);

CREATE TABLE event_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_time   TEXT NOT NULL,
    real_time   TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    actor_id    TEXT REFERENCES entities(id),
    description TEXT NOT NULL,
    changes     TEXT NOT NULL
);
```

- event_type: 'action', 'combat', 'dialogue', 'world_change', 'time_advance'
- changes: JSON of exact DB mutations applied
- Event log is the audit trail -- enables rollback and debugging

---

## 5. Time-Advance System (World Simulation)

The hardest problem. When time passes (sleep, imprisonment, travel), NPCs with active goals should advance.

### 5.1 Goal-Driven Fast-Forward

NOT real-time simulation. NOT day-by-day. Instead:

1. Collect all NPCs with active goals
2. Assemble each NPC's context: goals, stats, location, relationships, knowledge
3. Single LLM call: "Time advanced by [duration]. What changed?"
4. LLM returns structured proposals per NPC
5. Validator checks each against constraints
6. Commit valid, reject impossible

### 5.2 Constraints

**Hard (automatic reject):**
- NPC cannot be in two locations at once
- Travel takes time (location graph with distances)
- Dead NPCs do nothing
- Imprisoned/restrained NPCs cannot travel
- Cannot use items not in inventory
- Cannot act on unknown knowledge

**Soft (flag, allow with justification):**
- Major relationship shifts need a cause
- Goal priority changes need a trigger
- Acquiring significant items needs a plausible source

### 5.3 NPC Agency Tiers

| Tier | Simulation | Examples |
|------|------------|----------|
| Active | Full goal-driven | Villain, ally, rival |
| Reactive | Simple state update | Shopkeeper, guard |
| Background | None | Townsfolk |

Only Active tier costs LLM tokens during time-advance.

---

## 6. RPG Mechanics (Minimal Ruleset)

Inspired by In Nomine. Just enough mechanics to ground the LLM.

### 6.1 Resolution

Roll 2d6 against target number (stat + skill).
- Roll <= target = success (margin = target - roll)
- Natural 2 (snake eyes) = critical success
- Natural 12 = critical failure
- Contested: both roll, higher margin wins

### 6.2 Combat

- Initiative: ethereal + d6, highest goes first
- Attack: corporeal + fighting skill vs target's corporeal + dodge skill
- Damage: weapon base + margin of success
- Theater of mind, no grid, no movement squares

### 6.3 Character Creation

- Distribute 12 points across corporeal / ethereal / celestial (min 1, max 6)
- Pick 5 skills at rank 1-3
- Choose starting equipment from a list
- Write a one-paragraph background (stored in entities.notes, feeds LLM context)

---

## 7. LLM Contract

The narrator LLM must produce two blocks per turn:

```
[NARRATIVE]
The guard eyes you suspiciously as you approach the gate. "No one enters after dark,"
he growls, hand resting on his sword hilt.

[ACTIONS]
type: dialogue
npc: guard_north_gate
disposition_change: -5
knowledge_gained: guard now knows player wants entry at night
skill_check_needed: persuasion (ethereal + lying) target 8
```

Rules:
- If [ACTIONS] missing: parser flags, system re-prompts
- If [ACTIONS] contradict world state: validator rejects, LLM re-narrates
- LLM prompt includes: scene context, player action, character sheet, relevant world facts

---

## 8. Session History and Memory

### 8.1 Three Memory Layers

| Layer | Contents | Persistence | LLM Access |
|-------|----------|-------------|------------|
| World DB | Entities, components, facts | Permanent (SQLite) | Filtered by scene |
| Session Log | Scene summaries | Permanent (event_log) | Last N entries |
| Rolling Context | Raw LLM turns | Session only | Last M turns |

### 8.2 Scene Summarization (Gage-Style)

Every N turns (configurable, default 5-10):
1. Take raw turns since last summary
2. Ask LLM for concise narrator-voice summary
3. Store in event_log
4. Trim rolling context

Spine Reborn consolidation pattern. Prevents context overflow while maintaining narrative continuity.

---

## 9. Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python | Consistent with all projects |
| Database | SQLite | Single file, portable, sufficient for single-player |
| LLM | Ollama (gemma3:12b) | Local, profiled, known strengths/weaknesses |
| UI | Terminal-first, PyQt6 later | Fast to prototype |
| Dice | Python random | Simple, seedable |

---

## 10. Build Phases

| Phase | Scope | Delivers |
|-------|-------|----------|
| 0 | DB schema + CRUD + character creation | Testable world state |
| 1 | Scene assembler + LLM narrator + action parser | First playable turn |
| 2 | Rules engine + validator | Mechanical integrity |
| 3 | Time-advance system | Living world |
| 4 | Session history + Gage summarization | Long campaigns |
| 5 | PyQt6 UI | Polished experience |
| 6 | World-building tools, scenario editor, save/load | Content creation |

---

## 11. Open Questions

1. **Project name?** -- needs one before Phase 0
2. **Genre/setting?** -- engine is genre-agnostic but first scenario needs a setting to test with
3. **Single character or party?** -- party adds NPC companion management complexity
4. **Narration vs mechanics ratio?** -- slider between "novel" and "roguelike"
5. **Show dice rolls?** -- transparency vs immersion
6. **Terminal-first or GUI-first?** -- terminal faster to prototype
7. **NPC death during time-advance?** -- plot NPCs need protection flags or chaos ensues
