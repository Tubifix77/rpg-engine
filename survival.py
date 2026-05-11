"""survival.py - Hunger, thirst, fatigue condition system.
Ticks counters up over time, maps thresholds to conditions,
provides stat penalties. LLM only sees the condition word."""

THRESHOLDS = {
    "hunger": [
        (75, "starving", {"strength": -2, "agility": -1}),
        (50, "hungry", {"strength": -1}),
        (25, "peckish", {}),
    ],
    "thirst": [
        (75, "dehydrated", {"will": -2, "perception": -1}),
        (50, "thirsty", {"perception": -1}),
        (25, "parched", {}),
    ],
    "fatigue": [
        (75, "exhausted", {"agility": -2, "intelligence": -1}),
        (50, "tired", {"agility": -1}),
        (25, "weary", {}),
    ],
}


class SurvivalSystem:
    def __init__(self, db):
        self.db = db

    def get_conditions(self, entity_id):
        """Return active survival conditions and total penalties."""
        s = self.db.get_survival(entity_id)
        conditions = []
        penalties = {}
        for stat_name, val in [("hunger", s["hunger"]),
                                ("thirst", s["thirst"]),
                                ("fatigue", s["fatigue"])]:
            for threshold, cond_name, pens in THRESHOLDS[stat_name]:
                if val >= threshold:
                    conditions.append(cond_name)
                    for k, v in pens.items():
                        penalties[k] = penalties.get(k, 0) + v
                    break  # only highest threshold per stat
        return conditions, penalties

    def tick(self, entity_id, hours=1):
        """Advance survival counters. Call on time skip."""
        h_rate = 2 * hours   # hunger per hour
        t_rate = 3 * hours   # thirst faster
        f_rate = 1 * hours   # fatigue slow
        return self.db.tick_survival(entity_id, h_rate, t_rate, f_rate)

    def eat(self, entity_id, amount=30):
        """Reduce hunger."""
        s = self.db.get_survival(entity_id)
        new_h = max(0, s["hunger"] - amount)
        self.db.set_survival(entity_id, new_h, s["thirst"], s["fatigue"])
        return new_h

    def drink(self, entity_id, amount=40):
        """Reduce thirst."""
        s = self.db.get_survival(entity_id)
        new_t = max(0, s["thirst"] - amount)
        self.db.set_survival(entity_id, s["hunger"], new_t, s["fatigue"])
        return new_t

    def rest(self, entity_id, hours=8):
        """Reduce fatigue based on rest hours."""
        s = self.db.get_survival(entity_id)
        reduction = hours * 10
        new_f = max(0, s["fatigue"] - reduction)
        self.db.set_survival(entity_id, s["hunger"], s["thirst"], new_f)
        return new_f

    def format_for_scene(self, entity_id):
        """Short string for scene assembler. Empty if all fine."""
        conds, _ = self.get_conditions(entity_id)
        return ", ".join(conds) if conds else ""
