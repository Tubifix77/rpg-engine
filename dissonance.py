"""dissonance.py - Moral consequence system.
Each Choir/Band has specific Dissonance triggers.
Accumulated Dissonance can manifest as Discord."""
from dice import skill_check
import random

# Choir dissonance conditions (angel)
CHOIR_DISSONANCE = {
    "seraph": {"trigger": "lying", "keywords": ["lie", "deceive", "mislead", "false"], "desc": "Seraphim gain Dissonance from lying"},
    "cherub": {"trigger": "charge_harmed", "keywords": ["abandon", "betray"], "desc": "Cherubim gain Dissonance when their charge is harmed"},
    "ofanite": {"trigger": "immobility", "keywords": ["stay", "wait", "remain", "still"], "desc": "Ofanim gain Dissonance from staying still too long"},
    "elohite": {"trigger": "emotion", "keywords": ["angry", "furious", "jealous", "hate", "love"], "desc": "Elohim gain Dissonance from acting on emotion"},
    "malakite": {"trigger": "oath_break", "keywords": ["break oath", "dishonor", "coward"], "desc": "Malakim gain Dissonance from breaking Oaths"},
    "kyriotate": {"trigger": "host_harm", "keywords": ["damage host", "harm host"], "desc": "Kyriotates gain Dissonance from leaving a host worse"},
    "mercurian": {"trigger": "harm_human", "keywords": ["kill", "attack", "hurt", "harm", "strike", "punch", "stab", "shoot"], "desc": "Mercurians gain Dissonance from directly harming humans"},
}

# Band dissonance conditions (demon)
BAND_DISSONANCE = {
    "balseraph": {"trigger": "truth_revealed", "keywords": ["truth", "exposed", "caught lying"], "desc": "Balseraphs gain Dissonance when their lies are exposed"},
    "djinn": {"trigger": "show_care", "keywords": ["care", "protect", "love", "compassion"], "desc": "Djinn gain Dissonance from showing genuine care"},
    "calabite": {"trigger": "fail_destroy", "keywords": ["spare", "mercy", "restrain"], "desc": "Calabim gain Dissonance from failing to destroy"},
    "habbalite": {"trigger": "positive_emotion", "keywords": ["happy", "joy", "grateful", "kind"], "desc": "Habbalah gain Dissonance from feeling positive emotions"},
    "lilim": {"trigger": "geas_unfulfilled", "keywords": ["owe", "debt", "obligation"], "desc": "Lilim gain Dissonance from unfulfilled Geasa"},
    "shedite": {"trigger": "fail_corrupt", "keywords": ["pure", "innocent", "resist"], "desc": "Shedim gain Dissonance from failing to corrupt their host"},
    "impudite": {"trigger": "kill_human", "keywords": ["kill", "murder", "slay", "execute"], "desc": "Impudites gain Dissonance from killing humans"},
}

# Discord options by realm
DISCORD_OPTIONS = {
    "corporeal": [
        ("Crippled", "Reduced agility, movement impaired"),
        ("Ugly", "Social interactions suffer, humans recoil"),
        ("Fragile", "Reduced maximum HP"),
        ("Bound", "Cannot leave a specific area"),
    ],
    "ethereal": [
        ("Absent-minded", "Reduced intelligence, forgets details"),
        ("Paranoid", "False Disturbance alerts, trust issues"),
        ("Compulsive", "Must repeat specific behaviors"),
        ("Nightmares", "Fatigue from disturbed sleep"),
    ],
    "celestial": [
        ("Aura of Unease", "Humans feel uncomfortable nearby"),
        ("Vulnerable", "Extra damage from opposing faction powers"),
        ("Discolored", "Vessel shows supernatural signs"),
        ("Need", "Compulsive craving that must be satisfied"),
    ],
}


class DissonanceSystem:
    def __init__(self, db):
        self.db = db

    def check_action(self, entity_id, action, action_text=""):
        """Check if action triggers Dissonance for this entity.
        Returns (triggered, reason) tuple."""
        sup = self.db.get_supernatural(entity_id)
        if not sup:
            return False, ""
        nature = sup.get("nature", "human")
        if nature == "human":
            return False, ""

        choir = sup.get("choir_or_band", "")
        if not choir:
            return False, ""
        choir = choir.lower().strip()

        # Look up in angel or demon table
        if nature in ("angel", "redeemed"):
            cond = CHOIR_DISSONANCE.get(choir)
        elif nature in ("demon", "fallen"):
            cond = BAND_DISSONANCE.get(choir)
        else:
            return False, ""

        if not cond:
            return False, ""

        # Keyword scan against action text
        text = action_text.lower()
        atype = action.get("type", "").lower()
        combined = f"{text} {atype} {action.get('npc', '')} {action.get('target', '')}".lower()
        for kw in cond["keywords"]:
            if kw in combined:
                return True, cond["desc"]
        return False, ""

    def apply_dissonance(self, entity_id, reason=""):
        """Add 1 Dissonance and check for Discord."""
        sup = self.db.add_dissonance(entity_id, 1)
        dis = sup["dissonance"]
        result = {"dissonance": dis, "reason": reason}

        # Discord check at 5+ Dissonance
        if dis >= 5:
            stats = self.db.get_stats(entity_id)
            will_val = stats.get("will", 3) if stats else 3
            roll = skill_check(will_val, 0)
            if not roll["success"]:
                # Failed Will check: gain Discord
                discord = self._assign_discord(entity_id)
                result["discord_gained"] = discord
                # Reset Dissonance
                self.db.db.execute(
                    "UPDATE comp_supernatural SET dissonance=0 WHERE entity_id=?",
                    (entity_id,))
                self.db.db.commit()
                result["dissonance"] = 0
            else:
                result["discord_resisted"] = True
        return result

    def _assign_discord(self, entity_id):
        """Assign a random Discord."""
        realm = random.choice(["corporeal", "ethereal", "celestial"])
        options = DISCORD_OPTIONS[realm]
        name, desc = random.choice(options)
        # Check if already has this Discord (level up)
        existing = self.db.get_discord(entity_id)
        for d in existing:
            if d["discord_name"] == name:
                new_lvl = d["level"] + 1
                self.db.add_discord(entity_id, name, new_lvl, realm, desc)
                return {"name": name, "level": new_lvl, "realm": realm, "desc": desc}
        self.db.add_discord(entity_id, name, 1, realm, desc)
        return {"name": name, "level": 1, "realm": realm, "desc": desc}

    def format_result(self, result):
        """Format for mechanics display."""
        parts = [f"Dissonance: {result['dissonance']}"]
        if result.get("reason"):
            parts.append(f"({result['reason']})")
        if result.get("discord_gained"):
            d = result["discord_gained"]
            parts.append(f"DISCORD GAINED: {d['name']} ({d['realm']}, level {d['level']}) — {d['desc']}")
        if result.get("discord_resisted"):
            parts.append("(Discord resisted — Will held)")
        return " | ".join(parts)
