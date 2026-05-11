"""test_schema.py - Validate the RPG World Engine database schema."""
import sqlite3
import uuid
import json
import sys

DB = ":memory:"

SCHEMA = """
CREATE TABLE entities (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    destroyed_at TEXT,
    notes       TEXT
);

CREATE TABLE comp_physical (
    entity_id       TEXT PRIMARY KEY REFERENCES entities(id),
    hp_current      INTEGER NOT NULL,
    hp_max          INTEGER NOT NULL,
    location_id     TEXT REFERENCES entities(id),
    conditions      TEXT,
    is_alive        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE comp_stats (
    entity_id   TEXT PRIMARY KEY REFERENCES entities(id),
    corporeal   INTEGER NOT NULL DEFAULT 3,
    ethereal    INTEGER NOT NULL DEFAULT 3,
    celestial   INTEGER NOT NULL DEFAULT 3,
    skills      TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE comp_inventory (
    item_id     TEXT REFERENCES entities(id),
    holder_id   TEXT REFERENCES entities(id),
    equipped    INTEGER NOT NULL DEFAULT 0,
    quantity    INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (item_id, holder_id)
);

CREATE TABLE comp_location (
    entity_id       TEXT PRIMARY KEY REFERENCES entities(id),
    parent_id       TEXT REFERENCES entities(id),
    description     TEXT,
    current_state   TEXT,
    connections     TEXT,
    is_accessible   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE comp_relationships (
    entity_a    TEXT REFERENCES entities(id),
    entity_b    TEXT REFERENCES entities(id),
    rel_type    TEXT NOT NULL,
    value       INTEGER,
    details     TEXT,
    PRIMARY KEY (entity_a, entity_b, rel_type)
);

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

CREATE TABLE comp_goals (
    id          TEXT PRIMARY KEY,
    entity_id   TEXT REFERENCES entities(id),
    description TEXT NOT NULL,
    priority    INTEGER NOT NULL DEFAULT 5,
    status      TEXT NOT NULL DEFAULT 'active',
    deadline    TEXT,
    blockers    TEXT
);

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
"""

def uid():
    return str(uuid.uuid4())[:8]

def run_tests():
    db = sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys = ON")
    passed = 0
    failed = 0

    # --- Test 1: Create schema ---
    try:
        db.executescript(SCHEMA)
        print("PASS: Schema created")
        passed += 1
    except Exception as e:
        print(f"FAIL: Schema creation: {e}")
        failed += 1
        return passed, failed

    # --- Test 2: Create locations ---
    loc_town = uid()
    loc_gate = uid()
    loc_tavern = uid()
    try:
        db.execute("INSERT INTO entities VALUES (?,?,?,?,?,?)", (loc_town, "location", "Millhaven", "day 1", None, None))
        db.execute("INSERT INTO entities VALUES (?,?,?,?,?,?)", (loc_gate, "location", "North Gate", "day 1", None, None))
        db.execute("INSERT INTO entities VALUES (?,?,?,?,?,?)", (loc_tavern, "location", "The Rusty Flagon", "day 1", None, None))
        conns = json.dumps({"north": loc_gate, "tavern": loc_tavern})
        db.execute("INSERT INTO comp_location VALUES (?,?,?,?,?,?)",
            (loc_town, None, "A quiet farming town", None, conns, 1))
        db.execute("INSERT INTO comp_location VALUES (?,?,?,?,?,?)",
            (loc_gate, loc_town, "Heavy oak gate", "closed at night", json.dumps({"south": loc_town}), 1))
        db.execute("INSERT INTO comp_location VALUES (?,?,?,?,?,?)",
            (loc_tavern, loc_town, "Smoky tavern", None, json.dumps({"outside": loc_town}), 1))
        print("PASS: Locations created with connections")
        passed += 1
    except Exception as e:
        print(f"FAIL: Locations: {e}")
        failed += 1

    # --- Test 3: Create NPC with stats ---
    npc_guard = uid()
    try:
        db.execute("INSERT INTO entities VALUES (?,?,?,?,?,?)",
            (npc_guard, "npc", "Gate Guard", "day 1", None, "Surly veteran"))
        db.execute("INSERT INTO comp_physical VALUES (?,?,?,?,?,?)",
            (npc_guard, 20, 20, loc_gate, "[]", 1))
        skills = json.dumps({"fighting": 3, "intimidation": 2})
        db.execute("INSERT INTO comp_stats VALUES (?,?,?,?,?)",
            (npc_guard, 4, 2, 3, skills))
        print("PASS: NPC with physical + stats")
        passed += 1
    except Exception as e:
        print(f"FAIL: NPC creation: {e}")
        failed += 1

    # --- Test 4: Create player ---
    player = uid()
    try:
        db.execute("INSERT INTO entities VALUES (?,?,?,?,?,?)",
            (player, "player", "Kael", "day 1", None, "A wandering sellsword"))
        db.execute("INSERT INTO comp_physical VALUES (?,?,?,?,?,?)",
            (player, 25, 25, loc_tavern, "[]", 1))
        p_skills = json.dumps({"fighting": 2, "persuasion": 1, "stealth": 2, "perception": 1, "survival": 1})
        db.execute("INSERT INTO comp_stats VALUES (?,?,?,?,?)",
            (player, 4, 4, 3, 3, 5, 4, p_skills))
        print("PASS: Player created")
        passed += 1
    except Exception as e:
        print(f"FAIL: Player: {e}")
        failed += 1

    # --- Test 5: Inventory ---
    sword = uid()
    potion = uid()
    try:
        db.execute("INSERT INTO entities VALUES (?,?,?,?,?,?)",
            (sword, "item", "Iron Sword", "day 1", None, "A worn but serviceable blade"))
        db.execute("INSERT INTO entities VALUES (?,?,?,?,?,?)",
            (potion, "item", "Healing Potion", "day 1", None, "Restores 10 HP"))
        db.execute("INSERT INTO comp_inventory VALUES (?,?,?,?)",
            (sword, player, 1, 1))
        db.execute("INSERT INTO comp_inventory VALUES (?,?,?,?)",
            (potion, player, 0, 2))
        # Verify
        rows = db.execute(
            "SELECT e.name, i.equipped, i.quantity FROM comp_inventory i JOIN entities e ON e.id = i.item_id WHERE i.holder_id = ?",
            (player,)).fetchall()
        assert len(rows) == 2, f"Expected 2 items, got {len(rows)}"
        print(f"PASS: Inventory ({rows[0][0]}, {rows[1][0]})")
        passed += 1
    except Exception as e:
        print(f"FAIL: Inventory: {e}")
        failed += 1

    # --- Test 6: Relationships ---
    try:
        db.execute("INSERT INTO comp_relationships VALUES (?,?,?,?,?)",
            (npc_guard, player, "disposition", -10, "Suspicious of strangers"))
        db.execute("INSERT INTO comp_relationships VALUES (?,?,?,?,?)",
            (npc_guard, player, "rival", None, "Caught player sneaking"))
        # Two relationships between same pair
        rows = db.execute(
            "SELECT rel_type, value FROM comp_relationships WHERE entity_a = ?", (npc_guard,)).fetchall()
        assert len(rows) == 2
        print("PASS: Multiple relationship types")
        passed += 1
    except Exception as e:
        print(f"FAIL: Relationships: {e}")
        failed += 1

    # --- Test 7: Knowledge system ---
    fact1 = uid()
    try:
        db.execute("INSERT INTO world_facts VALUES (?,?,?,?,?)",
            (fact1, "secret", "The mayor murdered the merchant", "day 3", 0))
        # Guard knows (witnessed)
        db.execute("INSERT INTO comp_knowledge VALUES (?,?,?,?)",
            (npc_guard, fact1, "day 3", "witnessed"))
        # Player does NOT know
        knows = db.execute(
            "SELECT 1 FROM comp_knowledge WHERE entity_id = ? AND fact_id = ?",
            (player, fact1)).fetchone()
        assert knows is None, "Player should NOT know the secret"
        guard_knows = db.execute(
            "SELECT source FROM comp_knowledge WHERE entity_id = ? AND fact_id = ?",
            (npc_guard, fact1)).fetchone()
        assert guard_knows[0] == "witnessed"
        print("PASS: Knowledge asymmetry (guard knows, player doesn't)")
        passed += 1
    except Exception as e:
        print(f"FAIL: Knowledge: {e}")
        failed += 1

    # --- Test 8: Goals ---
    goal1 = uid()
    try:
        db.execute("INSERT INTO comp_goals VALUES (?,?,?,?,?,?,?)",
            (goal1, npc_guard, "Report murder to captain", 8, "active",
             "day 5", json.dumps(["find_captain"])))
        row = db.execute("SELECT description, priority, status FROM comp_goals WHERE entity_id = ?",
            (npc_guard,)).fetchone()
        assert row[2] == "active"
        print(f"PASS: NPC goal ({row[0]})")
        passed += 1
    except Exception as e:
        print(f"FAIL: Goals: {e}")
        failed += 1

    # --- Test 9: World clock ---
    try:
        db.execute("INSERT INTO world_clock VALUES (?,?,?,?)", (1, "day 1, morning", "spring", "overcast"))
        # Singleton check: second insert should fail
        try:
            db.execute("INSERT INTO world_clock VALUES (?,?,?,?)", (2, "day 2", "spring", "rain"))
            print("FAIL: World clock allowed second row")
            failed += 1
        except sqlite3.IntegrityError:
            print("PASS: World clock singleton enforced")
            passed += 1
    except Exception as e:
        print(f"FAIL: World clock: {e}")
        failed += 1

    # --- Test 10: Event log ---
    try:
        db.execute(
            "INSERT INTO event_log (game_time, real_time, event_type, actor_id, description, changes) VALUES (?,?,?,?,?,?)",
            ("day 1, morning", "2026-05-07T10:00:00", "action", player,
             "Kael entered The Rusty Flagon",
             json.dumps({"comp_physical.location_id": {"from": loc_town, "to": loc_tavern}})))
        row = db.execute("SELECT COUNT(*) FROM event_log").fetchone()
        assert row[0] == 1
        print("PASS: Event log with change tracking")
        passed += 1
    except Exception as e:
        print(f"FAIL: Event log: {e}")
        failed += 1

    # --- Test 11: Scene query (what Scene Assembler would do) ---
    try:
        # Get player location and everything in it
        p_loc = db.execute(
            "SELECT location_id FROM comp_physical WHERE entity_id = ?",
            (player,)).fetchone()[0]
        npcs_here = db.execute("""
            SELECT e.name, p.hp_current, s.corporeal, s.ethereal, s.celestial
            FROM comp_physical p
            JOIN entities e ON e.id = p.entity_id
            JOIN comp_stats s ON s.entity_id = p.entity_id
            WHERE p.location_id = ? AND e.type = 'npc'
        """, (p_loc,)).fetchall()
        loc_info = db.execute("""
            SELECT e.name, l.description, l.current_state, l.connections
            FROM comp_location l
            JOIN entities e ON e.id = l.entity_id
            WHERE l.entity_id = ?
        """, (p_loc,)).fetchone()
        print(f"PASS: Scene query - Player at {loc_info[0]}, {len(npcs_here)} NPCs present")
        passed += 1
    except Exception as e:
        print(f"FAIL: Scene query: {e}")
        failed += 1

    # --- Summary ---
    db.close()
    return passed, failed

if __name__ == "__main__":
    p, f = run_tests()
    print(f"\n{'='*40}")
    print(f"Results: {p} passed, {f} failed")
    sys.exit(0 if f == 0 else 1)
