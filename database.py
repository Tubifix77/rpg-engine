"""database.py - World state database. Source of truth."""
import sqlite3
import uuid
import json
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS entities (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    destroyed_at TEXT,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS comp_physical (
    entity_id       TEXT PRIMARY KEY REFERENCES entities(id),
    hp_current      INTEGER NOT NULL,
    hp_max          INTEGER NOT NULL,
    location_id     TEXT REFERENCES entities(id),
    conditions      TEXT,
    is_alive        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS comp_stats (
    entity_id   TEXT PRIMARY KEY REFERENCES entities(id),
    strength    INTEGER NOT NULL DEFAULT 3,
    agility     INTEGER NOT NULL DEFAULT 3,
    intelligence INTEGER NOT NULL DEFAULT 3,
    precision   INTEGER NOT NULL DEFAULT 3,
    will        INTEGER NOT NULL DEFAULT 3,
    perception  INTEGER NOT NULL DEFAULT 3,
    morale_threshold INTEGER NOT NULL DEFAULT 30,
    skills      TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS comp_inventory (
    item_id     TEXT REFERENCES entities(id),
    holder_id   TEXT REFERENCES entities(id),
    equipped    INTEGER NOT NULL DEFAULT 0,
    quantity    INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (item_id, holder_id)
);

CREATE TABLE IF NOT EXISTS comp_item_stats (
    entity_id    TEXT PRIMARY KEY REFERENCES entities(id),
    item_type    TEXT NOT NULL DEFAULT 'misc',
    weapon_base  INTEGER,
    weapon_type  TEXT,
    armor_value  INTEGER,
    weight       REAL,
    volume       REAL,
    value        INTEGER
);

CREATE TABLE IF NOT EXISTS comp_location (
    entity_id       TEXT PRIMARY KEY REFERENCES entities(id),
    parent_id       TEXT REFERENCES entities(id),
    description     TEXT,
    current_state   TEXT,
    connections     TEXT,
    is_accessible   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS comp_relationships (
    entity_a    TEXT REFERENCES entities(id),
    entity_b    TEXT REFERENCES entities(id),
    rel_type    TEXT NOT NULL,
    value       INTEGER,
    details     TEXT,
    PRIMARY KEY (entity_a, entity_b, rel_type)
);

CREATE TABLE IF NOT EXISTS world_facts (
    fact_id     TEXT PRIMARY KEY,
    category    TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    public      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS comp_knowledge (
    entity_id   TEXT REFERENCES entities(id),
    fact_id     TEXT REFERENCES world_facts(fact_id),
    learned_at  TEXT NOT NULL,
    source      TEXT,
    PRIMARY KEY (entity_id, fact_id)
);

CREATE TABLE IF NOT EXISTS comp_goals (
    id          TEXT PRIMARY KEY,
    entity_id   TEXT REFERENCES entities(id),
    description TEXT NOT NULL,
    priority    INTEGER NOT NULL DEFAULT 5,
    status      TEXT NOT NULL DEFAULT 'active',
    deadline    TEXT,
    blockers    TEXT
);

CREATE TABLE IF NOT EXISTS world_clock (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    current_time TEXT NOT NULL,
    season      TEXT,
    weather     TEXT
);

CREATE TABLE IF NOT EXISTS comp_supernatural (
    entity_id           TEXT PRIMARY KEY REFERENCES entities(id),
    nature              TEXT NOT NULL DEFAULT 'human',
    forces_corporeal    INTEGER NOT NULL DEFAULT 0,
    forces_ethereal     INTEGER NOT NULL DEFAULT 0,
    forces_celestial    INTEGER NOT NULL DEFAULT 0,
    essence             INTEGER NOT NULL DEFAULT 0,
    essence_max         INTEGER NOT NULL DEFAULT 0,
    dissonance          INTEGER NOT NULL DEFAULT 0,
    choir_or_band       TEXT,
    superior            TEXT
);

CREATE TABLE IF NOT EXISTS comp_songs (
    entity_id   TEXT REFERENCES entities(id),
    song_name   TEXT NOT NULL,
    realm       TEXT NOT NULL,
    level       INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (entity_id, song_name, realm)
);

CREATE TABLE IF NOT EXISTS comp_attunements (
    entity_id       TEXT REFERENCES entities(id),
    attunement_name TEXT NOT NULL,
    source          TEXT,
    description     TEXT,
    passive         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (entity_id, attunement_name)
);

CREATE TABLE IF NOT EXISTS comp_discord (
    entity_id       TEXT REFERENCES entities(id),
    discord_name    TEXT NOT NULL,
    level           INTEGER NOT NULL DEFAULT 1,
    realm           TEXT NOT NULL,
    description     TEXT,
    PRIMARY KEY (entity_id, discord_name)
);

CREATE TABLE IF NOT EXISTS comp_vessels (
    entity_id       TEXT REFERENCES entities(id),
    vessel_name     TEXT NOT NULL,
    vessel_level    INTEGER NOT NULL DEFAULT 1,
    vessel_hp       INTEGER NOT NULL DEFAULT 10,
    vessel_hp_max   INTEGER NOT NULL DEFAULT 10,
    PRIMARY KEY (entity_id, vessel_name)
);

CREATE TABLE IF NOT EXISTS comp_roles (
    entity_id       TEXT REFERENCES entities(id),
    role_name       TEXT NOT NULL,
    role_level      INTEGER NOT NULL DEFAULT 1,
    role_description TEXT,
    PRIMARY KEY (entity_id, role_name)
);

CREATE TABLE IF NOT EXISTS comp_economy (
    entity_id   TEXT PRIMARY KEY REFERENCES entities(id),
    currency    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS comp_survival (
    entity_id   TEXT PRIMARY KEY REFERENCES entities(id),
    hunger      INTEGER NOT NULL DEFAULT 0,
    thirst      INTEGER NOT NULL DEFAULT 0,
    fatigue     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS disturbance_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_time       TEXT NOT NULL,
    location_id     TEXT REFERENCES entities(id),
    source_entity_id TEXT REFERENCES entities(id),
    magnitude       INTEGER NOT NULL,
    song_name       TEXT
);

CREATE TABLE IF NOT EXISTS event_log (
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

class WorldDB:
    def __init__(self, path="world.db"):
        self.path = path
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    # --- Entity CRUD ---
    def create_entity(self, etype, name, time, notes=None):
        eid = uid()
        self.db.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?)",
            (eid, etype, name, time, None, notes))
        self.db.commit()
        return eid

    def get_entity(self, eid):
        row = self.db.execute(
            "SELECT * FROM entities WHERE id=?", (eid,)
        ).fetchone()
        return dict(row) if row else None

    def destroy_entity(self, eid, time):
        self.db.execute(
            "UPDATE entities SET destroyed_at=? WHERE id=?", (time, eid))
        self.db.commit()

    # --- Physical ---
    def set_physical(self, eid, hp, hp_max, loc_id, conditions=None):
        cond = json.dumps(conditions or [])
        self.db.execute(
            "INSERT OR REPLACE INTO comp_physical VALUES (?,?,?,?,?,?)",
            (eid, hp, hp_max, loc_id, cond, 1))
        self.db.commit()

    def get_physical(self, eid):
        row = self.db.execute(
            "SELECT * FROM comp_physical WHERE entity_id=?", (eid,)
        ).fetchone()
        if row:
            return dict(row)
        return None

    def update_hp(self, eid, delta):
        self.db.execute(
            "UPDATE comp_physical SET hp_current = MAX(0, MIN(hp_max, hp_current + ?)) WHERE entity_id=?",
            (delta, eid))
        self.db.commit()
        p = self.get_physical(eid)
        if p and p["hp_current"] <= 0:
            self.db.execute(
                "UPDATE comp_physical SET is_alive=0 WHERE entity_id=?", (eid,))
            self.db.commit()
        return p

    def move_entity(self, eid, new_loc):
        self.db.execute(
            "UPDATE comp_physical SET location_id=? WHERE entity_id=?",
            (new_loc, eid))
        self.db.commit()

    # --- Stats ---
    def set_stats(self, eid, strength, agility, intelligence, precision, will, perception, skills=None, morale=30):
        sk = json.dumps(skills or {})
        self.db.execute(
            "INSERT OR REPLACE INTO comp_stats VALUES (?,?,?,?,?,?,?,?,?)",
            (eid, strength, agility, intelligence, precision, will, perception, morale, sk))
        self.db.commit()

    def get_stats(self, eid):
        row = self.db.execute(
            "SELECT * FROM comp_stats WHERE entity_id=?", (eid,)
        ).fetchone()
        if row:
            d = dict(row)
            d["skills"] = json.loads(d["skills"])
            return d
        return None

    # --- Inventory ---
    def add_item(self, item_id, holder_id, equipped=0, qty=1):
        self.db.execute(
            "INSERT OR REPLACE INTO comp_inventory VALUES (?,?,?,?)",
            (item_id, holder_id, equipped, qty))
        self.db.commit()

    def remove_item(self, item_id, holder_id):
        self.db.execute(
            "DELETE FROM comp_inventory WHERE item_id=? AND holder_id=?",
            (item_id, holder_id))
        self.db.commit()

    def get_inventory(self, holder_id):
        rows = self.db.execute("""
            SELECT e.name, e.id, i.equipped, i.quantity
            FROM comp_inventory i
            JOIN entities e ON e.id = i.item_id
            WHERE i.holder_id = ?
        """, (holder_id,)).fetchall()
        return [dict(r) for r in rows]

    def has_item(self, item_id, holder_id):
        return self.db.execute(
            "SELECT 1 FROM comp_inventory WHERE item_id=? AND holder_id=?",
            (item_id, holder_id)).fetchone() is not None

    # --- Item Stats ---
    def set_item_stats(self, eid, item_type="misc", weapon_base=None, weapon_type=None, armor_value=None, weight=None, volume=None, value=None):
        self.db.execute(
            "INSERT OR REPLACE INTO comp_item_stats VALUES (?,?,?,?,?,?,?,?)",
            (eid, item_type, weapon_base, weapon_type, armor_value, weight, volume, value))
        self.db.commit()

    def get_item_stats(self, eid):
        row = self.db.execute(
            "SELECT * FROM comp_item_stats WHERE entity_id=?", (eid,)
        ).fetchone()
        return dict(row) if row else None

    def get_equipped_weapon(self, holder_id):
        row = self.db.execute("""
            SELECT s.* FROM comp_item_stats s
            JOIN comp_inventory i ON i.item_id = s.entity_id
            WHERE i.holder_id=? AND i.equipped=1
            AND s.item_type='weapon'
        """, (holder_id,)).fetchone()
        return dict(row) if row else None

    def get_equipped_armor(self, holder_id):
        row = self.db.execute("""
            SELECT s.* FROM comp_item_stats s
            JOIN comp_inventory i ON i.item_id = s.entity_id
            WHERE i.holder_id=? AND i.equipped=1
            AND s.item_type='armor'
        """, (holder_id,)).fetchone()
        return dict(row) if row else None

    # --- Economy ---
    def set_currency(self, eid, amount):
        self.db.execute(
            "INSERT OR REPLACE INTO comp_economy VALUES (?,?)",
            (eid, amount))
        self.db.commit()

    def get_currency(self, eid):
        row = self.db.execute(
            "SELECT currency FROM comp_economy WHERE entity_id=?", (eid,)
        ).fetchone()
        return row["currency"] if row else 0

    def update_currency(self, eid, delta):
        cur = self.get_currency(eid)
        new = max(0, cur + delta)
        self.set_currency(eid, new)
        return new

    # --- Survival ---
    def set_survival(self, eid, hunger=0, thirst=0, fatigue=0):
        self.db.execute(
            "INSERT OR REPLACE INTO comp_survival VALUES (?,?,?,?)",
            (eid, hunger, thirst, fatigue))
        self.db.commit()

    def get_survival(self, eid):
        row = self.db.execute(
            "SELECT * FROM comp_survival WHERE entity_id=?", (eid,)
        ).fetchone()
        return dict(row) if row else {"hunger": 0, "thirst": 0, "fatigue": 0}

    def tick_survival(self, eid, hunger_delta=1, thirst_delta=1, fatigue_delta=0):
        s = self.get_survival(eid)
        h = min(100, s["hunger"] + hunger_delta)
        t = min(100, s["thirst"] + thirst_delta)
        f = min(100, s["fatigue"] + fatigue_delta)
        self.set_survival(eid, h, t, f)
        return {"hunger": h, "thirst": t, "fatigue": f}

        # --- Supernatural ---
    def set_supernatural(self, eid, nature="human", f_corp=0, f_eth=0, f_cel=0, essence=0, essence_max=0, dissonance=0, choir_or_band=None, superior=None):
        self.db.execute(
            "INSERT OR REPLACE INTO comp_supernatural VALUES (?,?,?,?,?,?,?,?,?,?)",
            (eid, nature, f_corp, f_eth, f_cel, essence, essence_max, dissonance, choir_or_band, superior))
        self.db.commit()

    def get_supernatural(self, eid):
        row = self.db.execute(
            "SELECT * FROM comp_supernatural WHERE entity_id=?", (eid,)
        ).fetchone()
        return dict(row) if row else None

    def is_supernatural(self, eid):
        s = self.get_supernatural(eid)
        return s is not None and s.get("essence_max", 0) > 0

    def update_essence(self, eid, delta):
        self.db.execute(
            "UPDATE comp_supernatural SET essence = MAX(0, MIN(essence_max, essence + ?)) WHERE entity_id=?",
            (delta, eid))
        self.db.commit()
        return self.get_supernatural(eid)

    def add_dissonance(self, eid, amount=1):
        self.db.execute(
            "UPDATE comp_supernatural SET dissonance = dissonance + ? WHERE entity_id=?",
            (amount, eid))
        self.db.commit()
        return self.get_supernatural(eid)

    # --- Songs ---
    def add_song(self, eid, song_name, realm, level=1):
        self.db.execute(
            "INSERT OR REPLACE INTO comp_songs VALUES (?,?,?,?)",
            (eid, song_name, realm, level))
        self.db.commit()

    def get_songs(self, eid):
        rows = self.db.execute(
            "SELECT * FROM comp_songs WHERE entity_id=?", (eid,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Attunements ---
    def add_attunement(self, eid, name, source=None, desc=None, passive=0):
        self.db.execute(
            "INSERT OR REPLACE INTO comp_attunements VALUES (?,?,?,?,?)",
            (eid, name, source, desc, passive))
        self.db.commit()

    def get_attunements(self, eid):
        rows = self.db.execute(
            "SELECT * FROM comp_attunements WHERE entity_id=?", (eid,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Discord ---
    def add_discord(self, eid, name, level, realm, desc=None):
        self.db.execute(
            "INSERT OR REPLACE INTO comp_discord VALUES (?,?,?,?,?)",
            (eid, name, level, realm, desc))
        self.db.commit()

    def get_discord(self, eid):
        rows = self.db.execute(
            "SELECT * FROM comp_discord WHERE entity_id=?", (eid,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Vessels ---
    def add_vessel(self, eid, name, level=1, hp=10, hp_max=10):
        self.db.execute(
            "INSERT OR REPLACE INTO comp_vessels VALUES (?,?,?,?,?)",
            (eid, name, level, hp, hp_max))
        self.db.commit()

    def get_vessels(self, eid):
        rows = self.db.execute(
            "SELECT * FROM comp_vessels WHERE entity_id=?", (eid,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Roles ---
    def add_role(self, eid, name, level=1, desc=None):
        self.db.execute(
            "INSERT OR REPLACE INTO comp_roles VALUES (?,?,?,?)",
            (eid, name, level, desc))
        self.db.commit()

    def get_roles(self, eid):
        rows = self.db.execute(
            "SELECT * FROM comp_roles WHERE entity_id=?", (eid,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Disturbance ---
    def log_disturbance(self, game_time, loc_id, source_id, magnitude, song_name=None):
        self.db.execute(
            "INSERT INTO disturbance_log (game_time, location_id, source_entity_id, magnitude, song_name) VALUES (?,?,?,?,?)",
            (game_time, loc_id, source_id, magnitude, song_name))
        self.db.commit()

    def get_recent_disturbances(self, loc_id=None, n=10):
        if loc_id:
            rows = self.db.execute(
                "SELECT * FROM disturbance_log WHERE location_id=? ORDER BY id DESC LIMIT ?",
                (loc_id, n)).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM disturbance_log ORDER BY id DESC LIMIT ?",
                (n,)).fetchall()
        return [dict(r) for r in rows]

        # --- Location ---
    def set_location(self, eid, parent, desc, state, conns):
        c = json.dumps(conns or {})
        self.db.execute(
            "INSERT OR REPLACE INTO comp_location VALUES (?,?,?,?,?,?)",
            (eid, parent, desc, state, c, 1))
        self.db.commit()

    def get_location(self, eid):
        row = self.db.execute(
            "SELECT * FROM comp_location WHERE entity_id=?", (eid,)
        ).fetchone()
        if row:
            d = dict(row)
            d["connections"] = json.loads(d["connections"] or "{}")
            return d
        return None

    def get_entities_at(self, loc_id, etype=None):
        if etype:
            rows = self.db.execute("""
                SELECT e.* FROM entities e
                JOIN comp_physical p ON p.entity_id = e.id
                WHERE p.location_id=? AND e.type=? AND p.is_alive=1
            """, (loc_id, etype)).fetchall()
        else:
            rows = self.db.execute("""
                SELECT e.* FROM entities e
                JOIN comp_physical p ON p.entity_id = e.id
                WHERE p.location_id=? AND p.is_alive=1
            """, (loc_id,)).fetchall()
        return [dict(r) for r in rows]

    # --- Relationships ---
    def set_relationship(self, a, b, rtype, val=None, details=None):
        self.db.execute(
            "INSERT OR REPLACE INTO comp_relationships VALUES (?,?,?,?,?)",
            (a, b, rtype, val, details))
        self.db.commit()

    def get_relationships(self, eid):
        rows = self.db.execute(
            """SELECT r.*, e.name as other_name
            FROM comp_relationships r
            JOIN entities e ON e.id = CASE
                WHEN r.entity_a = ? THEN r.entity_b ELSE r.entity_a END
            WHERE r.entity_a = ? OR r.entity_b = ?""",
            (eid, eid, eid)).fetchall()
        return [dict(r) for r in rows]

    def get_disposition(self, a, b):
        row = self.db.execute(
            """SELECT value FROM comp_relationships
            WHERE entity_a=? AND entity_b=?
            AND rel_type='disposition'""",
            (a, b)).fetchone()
        return row["value"] if row else 0

    # --- Knowledge ---
    def add_fact(self, category, content, time, public=False):
        fid = uid()
        self.db.execute(
            "INSERT INTO world_facts VALUES (?,?,?,?,?)",
            (fid, category, content, time, 1 if public else 0))
        self.db.commit()
        return fid

    def teach_fact(self, eid, fact_id, time, source="witnessed"):
        self.db.execute(
            "INSERT OR IGNORE INTO comp_knowledge VALUES (?,?,?,?)",
            (eid, fact_id, time, source))
        self.db.commit()

    def knows_fact(self, eid, fact_id):
        return self.db.execute(
            "SELECT 1 FROM comp_knowledge WHERE entity_id=? AND fact_id=?",
            (eid, fact_id)).fetchone() is not None

    def get_knowledge(self, eid):
        rows = self.db.execute("""
            SELECT f.content, f.category, k.source, k.learned_at
            FROM comp_knowledge k
            JOIN world_facts f ON f.fact_id = k.fact_id
            WHERE k.entity_id = ?
        """, (eid,)).fetchall()
        return [dict(r) for r in rows]

    def get_public_facts(self):
        rows = self.db.execute(
            "SELECT * FROM world_facts WHERE public=1"
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Goals ---
    def add_goal(self, eid, desc, priority=5, deadline=None, blockers=None):
        gid = uid()
        bl = json.dumps(blockers or [])
        self.db.execute(
            "INSERT INTO comp_goals VALUES (?,?,?,?,?,?,?)",
            (gid, eid, desc, priority, "active", deadline, bl))
        self.db.commit()
        return gid

    def get_goals(self, eid, active_only=True):
        if active_only:
            rows = self.db.execute(
                "SELECT * FROM comp_goals WHERE entity_id=? AND status='active'",
                (eid,)).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM comp_goals WHERE entity_id=?",
                (eid,)).fetchall()
        return [dict(r) for r in rows]

    def update_goal(self, gid, status):
        self.db.execute(
            "UPDATE comp_goals SET status=? WHERE id=?",
            (status, gid))
        self.db.commit()

    # --- World Clock ---
    def init_clock(self, time, season, weather):
        self.db.execute(
            "INSERT OR REPLACE INTO world_clock VALUES (?,?,?,?)",
            (1, time, season, weather))
        self.db.commit()

    def get_clock(self):
        row = self.db.execute(
            "SELECT * FROM world_clock WHERE id=1"
        ).fetchone()
        return dict(row) if row else None

    def advance_clock(self, new_time, weather=None):
        if weather:
            self.db.execute(
                "UPDATE world_clock SET current_time=?, weather=? WHERE id=1",
                (new_time, weather))
        else:
            self.db.execute(
                "UPDATE world_clock SET current_time=? WHERE id=1",
                (new_time,))
        self.db.commit()

    # --- Event Log ---
    def log_event(self, game_time, event_type, actor_id, desc, changes):
        from datetime import datetime
        self.db.execute(
            """INSERT INTO event_log
            (game_time, real_time, event_type, actor_id, description, changes)
            VALUES (?,?,?,?,?,?)""",
            (game_time, datetime.now().isoformat(), event_type,
             actor_id, desc, json.dumps(changes)))
        self.db.commit()

    def get_recent_events(self, n=10):
        rows = self.db.execute(
            "SELECT * FROM event_log ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    # --- Convenience: get all active-tier NPCs ---
    def get_active_npcs(self):
        """NPCs that have at least one active goal."""
        rows = self.db.execute("""
            SELECT DISTINCT e.*
            FROM entities e
            JOIN comp_goals g ON g.entity_id = e.id
            JOIN comp_physical p ON p.entity_id = e.id
            WHERE e.type = 'npc'
            AND g.status = 'active'
            AND p.is_alive = 1
        """).fetchall()
        return [dict(r) for r in rows]

    # --- Find entity by name ---
    def find_entity(self, name):
        if not name or not name.strip():
            return None
        n = name.strip().lower()
        row = self.db.execute(
            "SELECT * FROM entities WHERE LOWER(name) = ? AND destroyed_at IS NULL",
            (n,)).fetchone()
        if row:
            return dict(row)
        row = self.db.execute(
            "SELECT * FROM entities WHERE LOWER(name) LIKE ? AND destroyed_at IS NULL",
            (f'%{n}%',)).fetchone()
        if row:
            return dict(row)
        return None
