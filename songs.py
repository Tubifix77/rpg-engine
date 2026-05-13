"""songs.py - In Nomine Song system.
Songs are Essence-fueled supernatural abilities.
Each Song has Corporeal/Ethereal/Celestial versions.
Using a Song costs Essence and generates Disturbance."""
from dice import skill_check

# Song definitions: data, not code
# stat = which stat governs this realm's version
# cost = Essence cost to perform
# effect = effect handler name
SONGS = {
    "healing": {
        "corporeal": {"stat": "strength", "cost": 1, "effect": "heal_hp"},
        "ethereal": {"stat": "intelligence", "cost": 2, "effect": "heal_mind"},
        "celestial": {"stat": "will", "cost": 3, "effect": "heal_soul"},
    },
    "thunder": {
        "corporeal": {"stat": "strength", "cost": 2, "effect": "damage"},
        "ethereal": {"stat": "intelligence", "cost": 2, "effect": "confusion"},
        "celestial": {"stat": "will", "cost": 3, "effect": "divine_damage"},
    },
    "shields": {
        "corporeal": {"stat": "strength", "cost": 1, "effect": "armor_buff"},
        "ethereal": {"stat": "intelligence", "cost": 2, "effect": "mental_shield"},
        "celestial": {"stat": "will", "cost": 2, "effect": "soul_shield"},
    },
    "motion": {
        "corporeal": {"stat": "strength", "cost": 1, "effect": "telekinesis"},
        "ethereal": {"stat": "intelligence", "cost": 2, "effect": "illusion"},
        "celestial": {"stat": "will", "cost": 3, "effect": "teleport"},
    },
    "tongues": {
        "corporeal": {"stat": "strength", "cost": 1, "effect": "speak_lang"},
        "ethereal": {"stat": "intelligence", "cost": 1, "effect": "read_emotions"},
        "celestial": {"stat": "will", "cost": 2, "effect": "divine_truth"},
    },
}


class SongSystem:
    def __init__(self, db):
        self.db = db

    def resolve_song(self, singer_id, song_name, realm, target_id=None):
        """Resolve a Song performance.
        Returns result dict for narrator."""
        sn = song_name.lower().strip()
        rm = realm.lower().strip()

        # Validate Song exists in definitions
        if sn not in SONGS:
            return {"success": False, "reason": f"Unknown Song: {song_name}"}
        if rm not in SONGS[sn]:
            return {"success": False, "reason": f"No {realm} version of {song_name}"}

        defn = SONGS[sn][rm]
        # Check singer knows this Song
        known = self.db.get_songs(singer_id)
        song_entry = None
        for s in known:
            if s["song_name"].lower() == sn and s["realm"].lower() == rm:
                song_entry = s
                break
        if not song_entry:
            return {"success": False, "reason": f"Singer doesn't know {realm} {song_name}"}

        song_level = song_entry["level"]
        cost = defn["cost"]

        # Check Essence
        sup = self.db.get_supernatural(singer_id)
        if not sup:
            return {"success": False, "reason": "Not a supernatural being"}
        if sup["essence"] < cost:
            return {"success": False, "reason": f"Not enough Essence ({sup['essence']}/{cost})"}

        # Spend Essence
        self.db.update_essence(singer_id, -cost)

        # Roll d666 vs (stat + song level)
        stats = self.db.get_stats(singer_id)
        stat_name = defn["stat"]
        stat_val = stats.get(stat_name, 3)
        roll = skill_check(stat_val, song_level)

        # Generate Disturbance: Essence spent + check digit on success
        dist = cost  # base: 1 per Essence
        if roll["success"]:
            dist += roll["check_digit"]

        # Log Disturbance
        clock = self.db.get_clock()
        gt = clock["current_time"] if clock else "unknown"
        phys = self.db.get_physical(singer_id)
        loc = phys["location_id"] if phys else None
        self.db.log_disturbance(gt, loc, singer_id, dist, sn)

        result = {
            "success": roll["success"],
            "song": sn,
            "realm": rm,
            "roll": roll,
            "essence_spent": cost,
            "essence_remaining": sup["essence"] - cost,
            "disturbance": dist,
            "intervention": roll["intervention"],
        }

        # Apply effect on success
        if roll["success"]:
            cd = roll["check_digit"]
            power = cd + song_level
            eff = defn["effect"]
            result["effect"] = self._apply_effect(eff, singer_id, target_id, power, cd)
        else:
            result["effect"] = "Song failed — Essence spent, Disturbance generated, no effect"

        return result

    def _apply_effect(self, effect, singer_id, target_id, power, cd):
        """Apply Song effect. Returns description string."""
        tid = target_id or singer_id

        if effect == "heal_hp":
            self.db.update_hp(tid, power)
            p = self.db.get_physical(tid)
            return f"Healed {power} HP (now {p['hp_current']}/{p['hp_max']})"

        elif effect == "heal_mind":
            return f"Cleared mental conditions (power {power})"

        elif effect == "heal_soul":
            if self.db.is_supernatural(tid):
                sup = self.db.get_supernatural(tid)
                old_d = sup["dissonance"]
                new_d = max(0, old_d - cd)
                self.db.db.execute("UPDATE comp_supernatural SET dissonance=? WHERE entity_id=?", (new_d, tid))
                self.db.db.commit()
                return f"Reduced Dissonance by {old_d - new_d} (now {new_d})"
            return f"Soul healing (power {power})"

        elif effect == "damage":
            arm = self.db.get_equipped_armor(tid)
            av = arm["armor_value"] if arm else 0
            dmg = max(0, power - av)
            self.db.update_hp(tid, -dmg)
            p = self.db.get_physical(tid)
            e = self.db.get_entity(tid)
            nm = e["name"] if e else "target"
            return f"Sonic blast: {dmg} damage to {nm} (armor absorbed {av}, HP {p['hp_current']}/{p['hp_max']})"

        elif effect == "divine_damage":
            # Ignores armor
            self.db.update_hp(tid, -power)
            p = self.db.get_physical(tid)
            e = self.db.get_entity(tid)
            nm = e["name"] if e else "target"
            return f"Divine wrath: {power} damage to {nm} (ignores armor, HP {p['hp_current']}/{p['hp_max']})"

        elif effect == "confusion":
            return f"Target confused for {cd} rounds"

        elif effect == "armor_buff":
            return f"Physical shield: +{cd} armor for the scene"

        elif effect == "mental_shield":
            return f"Mental shield: immune to mental effects for {cd} rounds"

        elif effect == "soul_shield":
            return f"Soul shield: immune to Dissonance for {cd} rounds"

        elif effect == "telekinesis":
            return f"Telekinesis: move objects up to {cd * 10}kg"

        elif effect == "illusion":
            return f"Illusory movement: appear elsewhere for {cd} rounds"

        elif effect == "teleport":
            return f"Teleported up to {cd * 100}m"

        elif effect == "speak_lang":
            return f"Speak any language for the scene"

        elif effect == "read_emotions":
            return f"Reading emotions: detect lies and surface thoughts (power {power})"

        elif effect == "divine_truth":
            return f"Divine truth: target must answer one question truthfully"

        return f"Effect: {effect} (power {power})"

    def format_result(self, r):
        """Format Song result for mechanics display."""
        if not r["success"]:
            if "reason" in r:
                return f"Song failed: {r['reason']}"
            return f"Song: {r['realm']} {r['song']} FAILED (Essence spent: {r['essence_spent']}, Disturbance: {r['disturbance']})"
        inter = ""
        if r.get("intervention"):
            inter = f" [{r['intervention'].upper()} INTERVENTION!]"
        return (f"Song: {r['realm']} {r['song']} SUCCESS{inter} — "
                f"{r['effect']}. Essence: {r['essence_remaining']}. "
                f"Disturbance: {r['disturbance']}")
