"""scene_assembler.py - Builds LLM context from world state."""
import json
from encumbrance import EncumbranceSystem
from survival import SurvivalSystem
from economy import EconomySystem

class SceneAssembler:
    def __init__(self, db):
        self.db = db
        self.enc = EncumbranceSystem(db)
        self.surv = SurvivalSystem(db)
        self.econ = EconomySystem(db)

    def _world_summary(self):
        """List all locations and living NPCs for narrator context."""
        locs = self.db.db.execute(
            "SELECT id, name FROM entities WHERE type='location' AND destroyed_at IS NULL"
        ).fetchall()
        loc_names = [r["name"] for r in locs]
        npcs = self.db.db.execute("""
            SELECT e.name, el.name as loc_name
            FROM entities e
            JOIN comp_physical p ON p.entity_id = e.id
            JOIN entities el ON el.id = p.location_id
            WHERE e.type = 'npc' AND p.is_alive = 1
        """).fetchall()
        npc_strs = [f"{r['name']} (at {r['loc_name']})" for r in npcs]
        return loc_names, npc_strs

    def assemble(self, player_id):
        """Build full scene context for LLM prompt."""
        player = self.db.get_entity(player_id)
        p_phys = self.db.get_physical(player_id)
        p_stats = self.db.get_stats(player_id)
        p_inv = self.db.get_inventory(player_id)
        p_knowledge = self.db.get_knowledge(player_id)
        loc_id = p_phys["location_id"]
        location = self.db.get_location(loc_id)
        loc_entity = self.db.get_entity(loc_id)
        npcs_here = self.db.get_entities_at(loc_id, "npc")
        clock = self.db.get_clock()
        recent = self.db.get_recent_events(5)
        # Build NPC details
        npc_details = []
        for npc in npcs_here:
            nid = npc["id"]
            n_stats = self.db.get_stats(nid)
            n_phys = self.db.get_physical(nid)
            disp = self.db.get_disposition(nid, player_id)
            n_knowledge = self.db.get_knowledge(nid)
            n_goals = self.db.get_goals(nid)
            npc_details.append({
                "name": npc["name"],
                "id": nid,
                "notes": npc.get("notes", ""),
                "hp": f"{n_phys['hp_current']}/{n_phys['hp_max']}" if n_phys else "?",
                "disposition": disp,
                "goals": [g["description"] for g in n_goals],
                "knows": [k["content"] for k in n_knowledge],
            })
        # Build context string
        parts = []
        parts.append("=== CURRENT SCENE ===")
        parts.append(f"Location: {loc_entity['name']}")
        parts.append(f"Description: {location['description']}")
        if location.get("current_state"):
            parts.append(f"State: {location['current_state']}")
        exits = ", ".join(f"{k} -> {self.db.get_entity(v)['name']}"
                          for k, v in location["connections"].items()
                          if self.db.get_entity(v))
        parts.append(f"Exits: {exits}")
        if clock:
            parts.append(f"Time: {clock['current_time']}, {clock['season']}, {clock['weather']}")
        parts.append("")
        # Player
        parts.append("=== PLAYER CHARACTER ===")
        parts.append(f"Name: {player['name']}")
        parts.append(f"HP: {p_phys['hp_current']}/{p_phys['hp_max']}")
        conds = json.loads(p_phys["conditions"] or "[]")
        if conds:
            parts.append(f"Conditions: {', '.join(conds)}")
        parts.append(f"STR:{p_stats['strength']} AGI:{p_stats['agility']} | INT:{p_stats['intelligence']} PRE:{p_stats['precision']} | WIL:{p_stats['will']} PER:{p_stats['perception']}")
        sk = ", ".join(f"{k}:{v}" for k, v in p_stats["skills"].items())
        parts.append(f"Skills: {sk}")
        if p_inv:
            inv = ", ".join(f"{i['name']}(x{i['quantity']}{'*' if i['equipped'] else ''})" for i in p_inv)
            parts.append(f"Inventory: {inv}")
        # Economy
        silver = self.econ.format_for_scene(player_id)
        parts.append(f"Currency: {silver}")
        # Encumbrance
        enc_txt = self.enc.format_for_scene(player_id)
        if enc_txt:
            parts.append(f"Encumbrance: {enc_txt}")
        # Survival conditions
        surv_txt = self.surv.format_for_scene(player_id)
        if surv_txt:
            parts.append(f"Physical state: {surv_txt}")
        # Supernatural context
        sup = self.db.get_supernatural(player_id)
        if sup and sup.get("essence_max", 0) > 0:
            nature = sup["nature"]
            choir = sup.get("choir_or_band", "")
            superior = sup.get("superior", "unknown")
            parts.append(f"Nature: {nature} ({choir} of {superior})")
            parts.append(f"Essence: {sup['essence']}/{sup['essence_max']}")
            if sup.get("dissonance", 0) > 0:
                parts.append(f"Dissonance: {sup['dissonance']}")
            songs = self.db.get_songs(player_id)
            if songs:
                sl = [s["song_name"] + "(" + s["realm"][0] + str(s["level"]) + ")" for s in songs]
                parts.append("Songs known: " + ", ".join(sl))
            disc = self.db.get_discord(player_id)
            for d in disc:
                parts.append("Discord: " + d["discord_name"] + " (level " + str(d["level"]) + ")")
            vessels = self.db.get_vessels(player_id)
            if vessels:
                v = vessels[0]
                parts.append("Vessel: " + v["vessel_name"] + " (level " + str(v["vessel_level"]) + ")")
        if player.get("notes"):
            parts.append(f"Background: {player['notes']}")
        if p_knowledge:
            facts = "; ".join(k["content"] for k in p_knowledge)
            parts.append(f"Player knows: {facts}")
        parts.append("")
        # NPCs
        if npc_details:
            parts.append("=== NPCs PRESENT ===")
            for n in npc_details:
                parts.append(f"- {n['name']} (HP:{n['hp']}, disposition:{n['disposition']})")
                if n["notes"]:
                    parts.append(f"  Description: {n['notes']}")
                if n["goals"]:
                    parts.append(f"  Goals: {'; '.join(n['goals'])}")
                if n["knows"]:
                    parts.append(f"  Knows: {'; '.join(n['knows'])}")
        else:
            parts.append("=== NPCs PRESENT ===")
            parts.append("None")
        parts.append("")
        # Recent history
        if recent:
            parts.append("=== RECENT EVENTS ===")
            for ev in recent:
                parts.append(f"[{ev['game_time']}] {ev['description']}")
        # Add world summary
        loc_names, all_npcs = self._world_summary()
        parts.append("")
        parts.append("=== WORLD LOCATIONS: " + ", ".join(loc_names) + " ===")
        parts.append("=== ALL LIVING NPCs: " + ", ".join(all_npcs) + " ===")
        parts.append("(NPCs may reference these in dialogue. Do NOT invent locations or NPCs not listed.)")
        # Add valid NPC list for LLM
        if npc_details:
            names = ", ".join(n["name"] for n in npc_details)
            parts.append("")
            parts.append(f"=== VALID NPC NAMES FOR [ACTIONS]: {names} ===")
            parts.append("(ONLY these names may appear in [ACTIONS]. ANY other name will be REJECTED by the rules engine)")
        return "\n".join(parts)

if __name__ == "__main__":
    from database import WorldDB
    import os
    TEST_DB = "test_scene.db"
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    db = WorldDB(TEST_DB)
    sa = SceneAssembler(db)
    # Build a small world
    town = db.create_entity("location", "Millhaven", "day 1")
    tavern = db.create_entity("location", "Rusty Flagon", "day 1")
    gate = db.create_entity("location", "North Gate", "day 1")
    db.set_location(town, None, "A quiet farming town", None, {"tavern": tavern, "north_gate": gate})
    db.set_location(tavern, town, "A smoky tavern with low beams", "crowded tonight", {"outside": town})
    db.set_location(gate, town, "Heavy oak gate", "closed", {"south": town})
    # Player
    p = db.create_entity("player", "Kael", "day 1", "A wandering sellsword seeking fortune")
    db.set_physical(p, 22, 25, tavern)
    db.set_stats(p, 4, 4, 3, 3, 5, 4, {"fighting": 2, "persuasion": 2, "stealth": 1, "perception": 1, "survival": 1})
    sword = db.create_entity("item", "Iron Sword", "day 1")
    pot = db.create_entity("item", "Healing Potion", "day 1")
    db.add_item(sword, p, equipped=1)
    db.add_item(pot, p, qty=2)
    # NPC in tavern
    barkeep = db.create_entity("npc", "Old Magda", "day 1", "Grizzled barkeeper, missing her left eye")
    db.set_physical(barkeep, 12, 12, tavern)
    db.set_stats(barkeep, 2, 2, 4, 4, 3, 3, {"perception": 3, "intimidation": 2})
    db.set_relationship(barkeep, p, "disposition", 10, "Likes paying customers")
    db.add_goal(barkeep, "Find out who stole the tavern's silver", 6)
    # A secret the barkeep knows
    f1 = db.add_fact("secret", "The mayor has been smuggling weapons", "day 1")
    db.teach_fact(barkeep, f1, "day 1", "witnessed")
    # Public fact
    f2 = db.add_fact("event", "The harvest festival is in three days", "day 1", public=True)
    db.teach_fact(p, f2, "day 1", "common_knowledge")
    # Clock
    db.init_clock("day 1, evening", "autumn", "light rain")
    # Event
    db.log_event("day 1, evening", "action", p,
                 "Kael entered the Rusty Flagon", {"moved_to": tavern})
    # Assemble and print
    print(sa.assemble(p))
    db.close()
    os.remove(TEST_DB)
