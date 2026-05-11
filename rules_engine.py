"""rules_engine.py - Deterministic game mechanics. No LLM."""
import json
from dice import skill_check, contested_check, initiative_roll, damage_roll

class RulesEngine:
    def __init__(self, db):
        self.db = db

    def resolve_skill_check(self, entity_id, skill_name, modifier=0):
        """Roll a skill check for an entity. Returns result dict."""
        stats = self.db.get_stats(entity_id)
        if not stats:
            return {"error": f"No stats for {entity_id}"}
        # Determine which realm the skill uses
        skill_rank = stats["skills"].get(skill_name, 0)
        stat_name = self._skill_stat(skill_name)
        stat_val = stats[stat_name]
        result = skill_check(stat_val, skill_rank, modifier)
        result["entity_id"] = entity_id
        result["skill"] = skill_name
        result["stat_name"] = stat_name
        result["stat"] = stat_val
        result["skill_rank"] = skill_rank
        return result

    def _skill_stat(self, skill_name):
        """Map skills to their governing stat."""
        m = {
            "fighting": "strength", "climbing": "strength",
            "swimming": "strength",
            "dodge": "agility", "stealth": "agility",
            "athletics": "agility",
            "lockpicking": "precision",
            "knowledge": "intelligence", "medicine": "intelligence",
            "survival": "intelligence", "crafting": "intelligence",
            "perception": "perception", "tracking": "perception",
            "investigation": "perception",
            "persuasion": "will", "intimidation": "will",
            "lying": "will", "diplomacy": "will",
            "leadership": "will", "performance": "will",
            "empathy": "will",
        }
        return m.get(skill_name, "strength")

    def resolve_combat_round(self, attacker_id, defender_id):
        """One round: both sides can deal damage."""
        a_phys = self.db.get_physical(attacker_id)
        d_phys = self.db.get_physical(defender_id)
        if not a_phys or not d_phys:
            return {"error": "Missing physical"}
        if not a_phys["is_alive"]:
            return {"error": "Attacker is dead"}
        if not d_phys["is_alive"]:
            return {"error": "Defender is dead"}
        a_stats = self.db.get_stats(attacker_id)
        d_stats = self.db.get_stats(defender_id)
        a_entity = self.db.get_entity(attacker_id)
        d_entity = self.db.get_entity(defender_id)
        a_name = a_entity["name"] if a_entity else "unknown"
        d_name = d_entity["name"] if d_entity else "unknown"
        a_fight = a_stats["skills"].get("fighting", 0)
        d_fight = d_stats["skills"].get("fighting", 0)
        d_dodge = d_stats["skills"].get("dodge", 0)
        # Contested roll
        attack = contested_check(
            a_stats["strength"], a_fight,
            d_stats["agility"], d_dodge)
        result = {
            "attacker": attacker_id,
            "defender": defender_id,
            "attacker_name": a_name,
            "defender_name": d_name,
            "hit": attack["winner"] == "a",
            "damage": 0,
            "defender_hp_max": d_phys["hp_max"],
            "counter_hit": False,
            "counter_damage": 0,
            "attacker_hp_max": a_phys["hp_max"],
        }
        # Weapon/armor lookup
        a_wpn = self.db.get_equipped_weapon(attacker_id)
        d_arm = self.db.get_equipped_armor(defender_id)
        wpn_base = a_wpn["weapon_base"] if a_wpn else 1
        arm_val = d_arm["armor_value"] if d_arm else 0
        if result["hit"]:
            cd = attack["roll_a"]["check_digit"]
            dmg = damage_roll(wpn_base, cd, armor=arm_val)
            result["damage"] = dmg
            result["armor_absorbed"] = arm_val
            p = self.db.update_hp(defender_id, -dmg)
            result["defender_hp"] = p["hp_current"]
            result["defender_alive"] = bool(p["is_alive"])
        else:
            result["defender_hp"] = d_phys["hp_current"]
            result["defender_alive"] = bool(d_phys["is_alive"])
        # Counter-attack: defender strikes back
        if attack["winner"] == "b" and result.get("defender_alive", True):
            c_cd = attack["roll_b"]["check_digit"]
            d_wpn = self.db.get_equipped_weapon(defender_id)
            a_arm = self.db.get_equipped_armor(attacker_id)
            c_wpn = d_wpn["weapon_base"] if d_wpn else 1
            c_arm = a_arm["armor_value"] if a_arm else 0
            c_dmg = damage_roll(c_wpn, c_cd, armor=c_arm)
            result["counter_hit"] = True
            result["counter_damage"] = c_dmg
            ap = self.db.update_hp(attacker_id, -c_dmg)
            result["attacker_hp"] = ap["hp_current"]
            result["attacker_alive"] = bool(ap["is_alive"])
        else:
            result["attacker_hp"] = a_phys["hp_current"]
            result["attacker_alive"] = bool(a_phys["is_alive"])
        # Morale check for defender
        if result.get("defender_alive", True):
            d_stats_m = self.db.get_stats(defender_id)
            if d_stats_m:
                threshold = d_stats_m.get("morale_threshold", 30)
                dp = self.db.get_physical(defender_id)
                hp_pct = (dp["hp_current"] / dp["hp_max"]) * 100
                if hp_pct <= threshold:
                    will_val = d_stats_m.get("will", 3)
                    morale_roll = skill_check(will_val, 0)
                    if not morale_roll["success"]:
                        result["defender_flees"] = True
                        result["morale_failed"] = True
        return result

    def can_move(self, entity_id, target_loc_id):
        """Check if entity can move to target location."""
        phys = self.db.get_physical(entity_id)
        if not phys:
            return False, "Entity has no physical presence"
        if not phys["is_alive"]:
            return False, "Entity is dead"
        conds = json.loads(phys["conditions"] or "[]")
        if "bound" in conds or "imprisoned" in conds:
            return False, "Entity is restrained"
        curr_loc = phys["location_id"]
        loc = self.db.get_location(curr_loc)
        if not loc:
            return False, "Current location not found"
        conns = loc["connections"]
        if target_loc_id not in conns.values():
            return False, f"No path from current location to target"
        target_loc = self.db.get_location(target_loc_id)
        if not target_loc:
            return False, "Target location not found"
        if not target_loc["is_accessible"]:
            return False, "Location is not accessible"
        return True, "OK"

    def execute_move(self, entity_id, target_loc_id):
        can, reason = self.can_move(entity_id, target_loc_id)
        if not can:
            return {"success": False, "reason": reason}
        old_loc = self.db.get_physical(entity_id)["location_id"]
        self.db.move_entity(entity_id, target_loc_id)
        return {"success": True, "from": old_loc, "to": target_loc_id}

    def use_item(self, entity_id, item_id):
        """Attempt to use an item. Returns result."""
        if not self.db.has_item(item_id, entity_id):
            return {"success": False, "reason": "Item not in inventory"}
        item = self.db.get_entity(item_id)
        if not item:
            return {"success": False, "reason": "Item not found"}
        name = item["name"].lower()
        # Healing potion
        if "healing" in name and "potion" in name:
            self.db.update_hp(entity_id, 10)
            self.db.remove_item(item_id, entity_id)
            p = self.db.get_physical(entity_id)
            return {"success": True, "effect": "healed 10 HP",
                    "hp": p["hp_current"]}
        return {"success": True, "effect": "used", "item": item["name"]}

if __name__ == "__main__":
    from database import WorldDB
    import os
    TEST_DB = "test_rules.db"
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    db = WorldDB(TEST_DB)
    rules = RulesEngine(db)
    # Setup test world
    loc = db.create_entity("location", "Arena", "day 1")
    db.set_location(loc, None, "A dusty arena", None, {})
    p = db.create_entity("player", "Kael", "day 1")
    db.set_physical(p, 25, 25, loc)
    db.set_stats(p, 4, 4, 3, 3, 5, 4, {"fighting": 2, "persuasion": 2, "stealth": 1})
    npc = db.create_entity("npc", "Bandit", "day 1")
    db.set_physical(npc, 15, 15, loc)
    db.set_stats(npc, 3, 3, 2, 2, 2, 2, {"fighting": 2, "dodge": 1})
    pot = db.create_entity("item", "Healing Potion", "day 1")
    db.add_item(pot, p)
    loc2 = db.create_entity("location", "Tavern", "day 1")
    db.set_location(loc2, None, "A tavern", None, {"arena": loc})
    # Connect arena to tavern
    db.set_location(loc, None, "A dusty arena", None, {"tavern": loc2})
    print("=== Rules Engine Tests ===")
    # Skill check
    r = rules.resolve_skill_check(p, "persuasion")
    print(f"Persuasion check: {r['success']} (roll {r['roll']} vs {r['target']}, {r['stat_name']})")
    # Combat
    r = rules.resolve_combat_round(p, npc)
    print(f"Combat: hit={r['hit']} dmg={r['damage']}")
    # Movement
    can, why = rules.can_move(p, loc2)
    print(f"Can move to tavern: {can} ({why})")
    r = rules.execute_move(p, loc2)
    print(f"Moved: {r}")
    # Can't move to nonexistent
    can, why = rules.can_move(p, "fake_id")
    print(f"Can move to fake: {can} ({why})")
    # Use potion
    r = rules.use_item(p, pot)
    print(f"Use potion: {r}")
    # Try again (consumed)
    r = rules.use_item(p, pot)
    print(f"Use potion again: {r}")
    db.close()
    os.remove(TEST_DB)
    print("All rules tests done.")
