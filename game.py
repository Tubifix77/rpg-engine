"""game.py - Main game loop. Ties all systems together."""
from database import WorldDB
from scene_assembler import SceneAssembler
from narrator import Narrator
from action_parser import ActionParser
from validator import Validator
from rules_engine import RulesEngine
from seed_world import seed
from plausibility import PlausibilityEngine
import os, sys

class Game:
    def __init__(self, db_path="world.db", model="gemma3:12b"):
        self.db_path = db_path
        self.model = model
        self.world = None
        self.player_id = None

    def start_new(self):
        """Seed a new world and start playing."""
        w = seed(self.db_path)
        self.world = w
        self.db = w["db"]
        self.player_id = w["player"]
        self._init_systems()

    def load_existing(self, player_id):
        """Load an existing world."""
        self.db = WorldDB(self.db_path)
        self.player_id = player_id
        self._init_systems()

    def _init_systems(self):
        """Initialize all subsystems and warm up the LLM."""
        self.scene = SceneAssembler(self.db)
        self.narrator = Narrator(model=self.model)
        self.parser = ActionParser()
        self.validator = Validator(self.db)
        self.rules = RulesEngine(self.db)
        self.plausibility = PlausibilityEngine(model=self.model)
        self.turn_count = 0
        # Warm up LLM - loads model into GPU memory
        if not self.narrator.warmup():
            print("WARNING: Narrator unavailable. Game will run but LLM responses will be errors.")

    def play_turn(self, player_input):
        """Two-pass game turn: resolve mechanics, then narrate."""
        self.turn_count += 1
        context = self.scene.assemble(self.player_id)
        # PASS 1: Determine actions (fast, no streaming)
        print("(resolving...)", end="", flush=True)
        raw_actions = self.narrator.resolve_actions(context, player_input)
        parsed = self.parser.parse("[ACTIONS]\n" + raw_actions if "[ACTIONS]" not in raw_actions else raw_actions)
        print("\r              \r", end="", flush=True)
        # Validate
        valid, violations = self.validator.validate(
            parsed["actions"], self.player_id, player_input)
        # Plausibility check
        plaus_results = self.plausibility.check(context, player_input, valid)
        plaus_debug = self.plausibility.format_debug(plaus_results)
        if plaus_debug:
            print(plaus_debug)
        # Filter actions by plausibility
        plaus_valid = []
        plaus_checks = []
        for action, rating, skill, reason in plaus_results:
            if rating == "AUTO":
                plaus_valid.append(action)
            elif rating == "CHECK":
                # Run the skill check, if pass then allow
                if skill and skill != "none":
                    check = self.rules.resolve_skill_check(self.player_id, skill)
                    plaus_checks.append(check)
                    if check["success"]:
                        plaus_valid.append(action)
                    else:
                        violations.append({"action": action,
                            "reason": f"Failed {skill} check for: {reason}"})
                else:
                    plaus_valid.append(action)  # no skill specified, allow
            elif rating == "IMPOSSIBLE":
                violations.append({"action": action,
                    "reason": f"Impossible: {reason}"})
        valid = plaus_valid
        # Execute: movements FIRST, then re-validate others at new location
        results = list(plaus_checks)
        move_actions = [a for a in valid if a.get("type") == "movement"]
        other_actions = [a for a in valid if a.get("type") != "movement"]
        # Execute movements first
        for action in move_actions:
            r = self._execute_action(action)
            if r:
                results.append(r)
        # Re-validate remaining actions at (possibly new) location
        if move_actions and other_actions:
            revalid, reviol = self.validator.validate(
                other_actions, self.player_id, player_input)
            other_actions = revalid
            violations.extend(reviol)
        # Execute remaining actions
        for action in other_actions:
            r = self._execute_action(action)
            if r:
                results.append(r)
        # Format mechanical results for display AND for narrator
        mech_text = self._compose_mechanics(results, violations)
        if mech_text:
            print(mech_text)
        # Add player location FIRST in mech text
        phys = self.db.get_physical(self.player_id)
        if phys:
            loc_ent = self.db.get_entity(phys["location_id"])
            if loc_ent:
                loc_note = f"IMPORTANT - PLAYER IS AT: {loc_ent['name']}. The player has NOT moved from here. Narrate ONLY from this location."
                mech_text = loc_note + "\n" + mech_text if mech_text else loc_note
        # PASS 2: Narrate outcome grounded in results (streaming)
        self.narrator.narrate_outcome(context, player_input, mech_text or "No mechanical effects.")
        # Log event
        clock = self.db.get_clock()
        game_time = clock["current_time"] if clock else "unknown"
        self.db.log_event(game_time, "action", self.player_id,
            player_input[:200],
            {"actions": [str(a) for a in valid],
                      "results": [str(r) for r in results]})
        return ""

    def _execute_action(self, action):
        atype = action.get("type", "")
        # COMBAT first - has priority over skill_check
        if atype == "combat":
            defender_name = action.get("defender", "") or action.get("npc", "")
            if not defender_name:
                return {"combat_error": "No target specified"}
            defender = self.db.find_entity(defender_name)
            if not defender:
                return {"combat_error": f"'{defender_name}' not found"}
            return self.rules.resolve_combat_round(
                self.player_id, defender["id"])
        # SKILL CHECK - but not if combat already handled
        elif "skill_check_needed" in action or atype == "skill_check":
            sc = str(action.get("skill_check_needed", ""))
            if not sc:
                return None
            skill = sc.split()[0]
            if not skill:
                return None
            return self.rules.resolve_skill_check(self.player_id, skill)
        elif atype == "movement":
            dest_name = action.get("destination", "")
            dest = self.db.find_entity(dest_name)
            if not dest:
                phys = self.db.get_physical(self.player_id)
                if phys:
                    loc = self.db.get_location(phys["location_id"])
                    if loc:
                        for k, eid in loc["connections"].items():
                            if k.lower() == dest_name.lower():
                                dest = self.db.get_entity(eid)
                                break
            if dest:
                return self.rules.execute_move(self.player_id, dest["id"])
        elif atype == "disposition_change":
            npc_name = action.get("npc", "")
            change = action.get("disposition_change", 0)
            npc = self.db.find_entity(npc_name)
            if npc and isinstance(change, int):
                old = self.db.get_disposition(npc["id"], self.player_id)
                new = max(-100, min(100, old + change))
                self.db.set_relationship(npc["id"],
                    self.player_id, "disposition", new)
                return {"disposition": f"{npc_name}: {old} -> {new}"}
        elif atype == "item_use":
            item_name = action.get("item", "")
            inv = self.db.get_inventory(self.player_id)
            for i in inv:
                if item_name.lower() in i["name"].lower():
                    return self.rules.use_item(self.player_id, i["id"])
        return None

    def _compose_mechanics(self, results, violations):
        """Only mechanical results and violations. Narrative already streamed."""
        parts = []
        if results:
            parts.append("--- Mechanical Results ---")
            for r in results:
                if isinstance(r, dict):
                    if "success" in r and "margin" in r:
                        s = "SUCCESS" if r["success"] else "FAILURE"
                        c = f" ({r['crit']})" if r.get("crit") else ""
                        parts.append(f"  [{r.get('skill','check')}] {s}{c} - rolled {r['roll']} vs {r['target']}")
                    elif "hit" in r:
                        h = "HIT" if r["hit"] else "MISS"
                        hp_info = ""
                        if "defender_hp" in r:
                            hp = r["defender_hp"]
                            mx = r.get("defender_hp_max", "?")
                            name = r.get("defender_name", "target")
                            alive = r.get("defender_alive", True)
                            status = "DEAD" if not alive else f"{hp}/{mx} HP"
                            hp_info = f" ({name}: {status})"
                        elif "defender_name" in r:
                            hp_info = f" ({r['defender_name']}: dodged)"
                        parts.append(f"  [combat] {h} - {r['damage']} damage{hp_info}")
                        if r.get("counter_hit"):
                            cn = r.get("defender_name", "NPC")
                            cd = r["counter_damage"]
                            ahp = r.get("attacker_hp", "?")
                            amx = r.get("attacker_hp_max", "?")
                            parts.append(f"  [counter] {cn} strikes back - {cd} damage (You: {ahp}/{amx} HP)")
                    elif "disposition" in r:
                        parts.append(f"  [disposition] {r['disposition']}")
                    elif "effect" in r:
                        parts.append(f"  [item] {r['effect']}")
                    elif "npc_moved" in r:
                        parts.append(f"  [drag] {r['npc_moved']}")
                    elif "combat_error" in r:
                        parts.append(f"  [combat] VOID - {r['combat_error']}")
                    else:
                        parts.append(f"  {r}")
        if violations:
            parts.append("\n--- Validator Warnings ---")
            for v in violations:
                parts.append(f"  REJECTED: {v['reason']}")
        return "\n".join(parts)

    def run(self):
        """Interactive terminal game loop."""
        print("=" * 60)
        print("  RPG WORLD ENGINE")
        print("  Type your actions. 'quit' to exit.")
        print("  'look' to see scene. 'inventory' to check items.")
        print("  'status' for character. 'debug' for raw scene.")
        print("=" * 60)
        # Show opening scene
        player = self.db.get_entity(self.player_id)
        phys = self.db.get_physical(self.player_id)
        loc_id = phys["location_id"]
        loc = self.db.get_entity(loc_id)
        loc_detail = self.db.get_location(loc_id)
        print(f"\nYou are {player['name']}, at {loc['name']}.")
        print(f"{loc_detail['description']}")
        if loc_detail.get("current_state"):
            print(f"({loc_detail['current_state']})")
        npcs = self.db.get_entities_at(loc_id, "npc")
        if npcs:
            names = ", ".join(n["name"] for n in npcs)
            print(f"Present: {names}")
        print()
        while True:
            try:
                action = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nFarewell, adventurer.")
                break
            if not action:
                continue
            if action.lower() == "quit":
                print("Farewell, adventurer.")
                break
            if action.lower() == "look":
                self._show_look()
                continue
            if action.lower() == "inventory":
                self._show_inventory()
                continue
            if action.lower() == "status":
                self._show_status()
                continue
            if action.lower() == "loot":
                self._show_loot()
                continue
            # Quick movement: single word matching an exit
            if len(action.split()) <= 2:
                phys = self.db.get_physical(self.player_id)
                if phys:
                    loc = self.db.get_location(phys["location_id"])
                    if loc:
                        exits = list(loc["connections"].keys())
                        word = action.lower().strip()
                        for ex in exits:
                            if ex.startswith(word[:3]) or word.startswith(ex[:3]):
                                dest_eid = loc["connections"][ex]
                                dest_ent = self.db.get_entity(dest_eid)
                                if dest_ent:
                                    r = self.rules.execute_move(self.player_id, dest_eid)
                                    if r and r.get("success"):
                                        print(f"(moved to {dest_ent['name']})")
                                        self._show_look()
                                    continue
            if action.lower() == "debug":
                print(self.scene.assemble(self.player_id))
                continue
            # Play a turn - narrative streams live
            print()
            mechanics = self.play_turn(action)
            if mechanics:
                print(mechanics)

            print()
        self.db.close()

    def _show_look(self):
        phys = self.db.get_physical(self.player_id)
        loc = self.db.get_entity(phys["location_id"])
        loc_d = self.db.get_location(phys["location_id"])
        print(f"\n{loc['name']}")
        print(f"{loc_d['description']}")
        if loc_d.get("current_state"):
            print(f"({loc_d['current_state']})")
        conns = loc_d["connections"]
        exits = ", ".join(f"{k}" for k in conns.keys())
        print(f"Exits: {exits}")
        npcs = self.db.get_entities_at(phys["location_id"], "npc")
        if npcs:
            for n in npcs:
                d = self.db.get_disposition(n["id"], self.player_id)
                mood = "hostile" if d < -20 else "wary" if d < 0 else "neutral" if d < 20 else "friendly"
                n_phys = self.db.get_physical(n["id"])
                if n_phys:
                    hp_str = f" HP:{n_phys['hp_current']}/{n_phys['hp_max']}"
                    alive = "" if n_phys["is_alive"] else " [DEAD]"
                else:
                    hp_str = ""
                    alive = ""
                print(f"  {n['name']} ({mood}{hp_str}{alive})")
        clock = self.db.get_clock()
        if clock:
            print(f"Time: {clock['current_time']}, {clock['weather']}")

    def _show_inventory(self):
        inv = self.db.get_inventory(self.player_id)
        if not inv:
            print("\nYou carry nothing.")
            return
        print("\nInventory:")
        for i in inv:
            eq = " [equipped]" if i["equipped"] else ""
            qty = f" x{i['quantity']}" if i["quantity"] > 1 else ""
            print(f"  {i['name']}{qty}{eq}")

    def _show_status(self):
        p = self.db.get_entity(self.player_id)
        phys = self.db.get_physical(self.player_id)
        stats = self.db.get_stats(self.player_id)
        print(f"\n{p['name']} - HP: {phys['hp_current']}/{phys['hp_max']}")
        import json
        conds = json.loads(phys["conditions"] or "[]")
        if conds:
            print(f"Conditions: {', '.join(conds)}")
        print(f"Corporeal: {stats['corporeal']} | Ethereal: {stats['ethereal']} | Celestial: {stats['celestial']}")
        sk = ", ".join(f"{k}:{v}" for k, v in stats["skills"].items())
        print(f"Skills: {sk}")
        knowledge = self.db.get_knowledge(self.player_id)
        if knowledge:
            print("Known facts:")
            for k in knowledge:
                print(f"  - {k['content']}")

    def _show_loot(self):
        """Show lootable NPCs at current location."""
        phys = self.db.get_physical(self.player_id)
        loc_id = phys["location_id"]
        npcs = self.db.get_entities_at(loc_id, "npc")
        dead = [n for n in npcs if not self.db.get_physical(n["id"])["is_alive"]]
        if not dead:
            print("Nothing to loot here.")
            return
        for n in dead:
            inv = self.db.get_inventory(n["id"])
            if inv:
                print(f"  {n['name']}'s items:")
                for item in inv:
                    self.db.remove_item(item["id"], n["id"])
                    self.db.add_item(item["id"], self.player_id)
                    print(f"    Taken: {item['name']}")
            else:
                print(f"  {n['name']} has nothing to loot.")

if __name__ == "__main__":
    game = Game()
    game.start_new()
    game.run()
