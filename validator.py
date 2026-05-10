"""validator.py - Check proposed actions against world state. v2 (playtest fixes)."""
import json

class Validator:
    def __init__(self, db):
        self.db = db

    def validate(self, actions, player_id, player_intent=""):
        valid = []
        violations = []
        for action in actions:
            ok, reason = self._check_action(action, player_id, player_intent)
            if ok:
                valid.append(action)
            else:
                violations.append({"action": action, "reason": reason})
        return valid, violations

    def _check_action(self, action, player_id, player_intent=""):
        atype = action.get("type", "unknown")
        # Fix 2: reject self-referencing actions
        npc_ref = action.get("npc", "") or action.get("defender", "") or action.get("target", "")
        if npc_ref:
            player = self.db.get_entity(player_id)
            if player and npc_ref.lower() == player["name"].lower():
                return False, "Action targets the player (self-referencing)"
        if atype == "movement":
            return self._check_movement(action, player_id, player_intent)
        elif atype == "combat":
            return self._check_combat(action, player_id)
        elif atype == "item_use":
            return self._check_item_use(action, player_id, player_intent)
        elif atype == "dialogue":
            return self._check_dialogue(action, player_id)
        elif atype == "disposition_change":
            return self._check_disposition(action, player_id)
        elif atype == "knowledge_transfer":
            return self._check_knowledge(action, player_id)
        elif atype == "skill_check":
            return True, "OK"
        return True, "OK"

    def _check_movement(self, action, player_id, player_intent=""):
        # Fix 5: only if player explicitly requested movement
        move_words = {"go", "walk", "move", "travel", "leave", "head", "run", "enter", "exit", "home", "north", "south", "east", "west", "outside", "inside", "upstairs", "downstairs", "gate", "tavern", "market", "temple"}
        if player_intent:
            words = set(player_intent.lower().split())
            if not words.intersection(move_words):
                return False, "Movement not requested by player"
        target = action.get("destination", "")
        if not target:
            return False, "No destination specified"
        if "->" in target:
            target = target.split("->")[-1].strip()
        entity = self.db.find_entity(target)
        if not entity:
            # Try matching connection key at current location
            phys_pre = self.db.get_physical(player_id)
            if phys_pre:
                loc_pre = self.db.get_location(phys_pre["location_id"])
                if loc_pre:
                    for key, eid in loc_pre["connections"].items():
                        if key.lower() == target.lower():
                            entity = self.db.get_entity(eid)
                            break
            if not entity:
                return False, f"Location '{target}' not found in world"
        if entity["type"] != "location":
            return False, 'not a location'
        phys = self.db.get_physical(player_id)
        if not phys or not phys['is_alive']:
            return False, 'Player is dead'
        loc = self.db.get_location(phys["location_id"])
        if entity["id"] not in loc["connections"].values():
            return False, f"No path to '{target}'"
        return True, "OK"

    def _check_combat(self, action, player_id):
        defender_name = action.get("defender", "") or action.get("npc", "")
        if not defender_name:
            return False, "No defender specified"
        defender = self.db.find_entity(defender_name)
        if not defender:
            return False, f"'{defender_name}' not found in world"
        if defender["type"] not in ("npc", "player"):
            return False, f"'{defender_name}' cannot be fought"
        d_phys = self.db.get_physical(defender["id"])
        if not d_phys or not d_phys["is_alive"]:
            return False, f"'{defender_name}' is dead"
        p_phys = self.db.get_physical(player_id)
        if d_phys["location_id"] != p_phys["location_id"]:
            return False, f"'{defender_name}' is not here"
        return True, "OK"

    def _check_item_use(self, action, player_id, player_intent=""):
        item_name = action.get("item", "")
        if not item_name:
            return False, "No item specified"
        # Fix 4: only if player explicitly mentioned item use
        if player_intent:
            use_words = {"use", "drink", "eat", "consume", "apply", "potion", "heal"}
            words = set(player_intent.lower().split())
            if not words.intersection(use_words):
                return False, "Item use not requested by player"
        inv = self.db.get_inventory(player_id)
        found = any(item_name.lower() in i["name"].lower() for i in inv)
        if not found:
            return False, f"'{item_name}' not in inventory"
        return True, "OK"

    def _check_dialogue(self, action, player_id):
        npc_name = action.get("npc", "")
        if not npc_name:
            return True, "OK"
        npc = self.db.find_entity(npc_name)
        if not npc:
            return False, f"NPC '{npc_name}' does not exist in world"
        if npc["type"] not in ("npc",):
            return False, f"'{npc_name}' is not an NPC"
        n_phys = self.db.get_physical(npc["id"])
        if not n_phys or not n_phys["is_alive"]:
            return False, f"NPC '{npc_name}' is dead"
        p_phys = self.db.get_physical(player_id)
        if n_phys["location_id"] != p_phys["location_id"]:
            return False, f"NPC '{npc_name}' is not here"
        return True, "OK"

    def _check_disposition(self, action, player_id):
        npc_name = action.get("npc", "")
        if not npc_name:
            return False, "No NPC specified for disposition"
        # Fix 1: reject unknown entities
        npc = self.db.find_entity(npc_name)
        if not npc:
            return False, f"NPC '{npc_name}' does not exist in world"
        change = action.get("disposition_change", 0)
        if not isinstance(change, (int, float)):
            return False, "Disposition change must be a number"
        # Check NPC alive
        n_phys_check = self.db.get_physical(npc["id"])
        if n_phys_check and not n_phys_check["is_alive"]:
            return False, f"NPC '{npc_name}' is dead"
        # Check NPC is at player location
        n_phys = self.db.get_physical(npc["id"])
        p_phys = self.db.get_physical(player_id)
        if n_phys and p_phys and n_phys["location_id"] != p_phys["location_id"]:
            return False, f"NPC '{npc_name}' is not at player location"
        if abs(change) > 30:
            return False, f"Disposition change {change} too extreme (max +/-30)"
        return True, "OK"

    def _check_knowledge(self, action, player_id):
        target = action.get("source_npc", "") or action.get("target", "")
        if not target:
            return True, "OK"
        entity = self.db.find_entity(target)
        if not entity:
            return False, f"'{target}' does not exist in world"
        return True, "OK"
