"""encumbrance.py - Inventory weight tracking and condition flags.
Reads item weights from comp_item_stats, sums per holder,
compares against Strength-derived capacity."""

class EncumbranceSystem:
    def __init__(self, db):
        self.db = db

    def get_carry_capacity(self, entity_id):
        """Capacity = Strength * 10 kg."""
        stats = self.db.get_stats(entity_id)
        if not stats:
            return 30  # default
        return stats["strength"] * 10

    def get_current_load(self, entity_id):
        """Sum weights of all carried items."""
        inv = self.db.get_inventory(entity_id)
        total = 0.0
        for item in inv:
            ist = self.db.get_item_stats(item["id"])
            if ist and ist.get("weight"):
                total += ist["weight"] * item.get("quantity", 1)
        return total

    def check_encumbrance(self, entity_id):
        """Returns condition string and load ratio."""
        cap = self.get_carry_capacity(entity_id)
        load = self.get_current_load(entity_id)
        ratio = load / cap if cap > 0 else 0
        if ratio >= 1.0:
            return "over_encumbered", load, cap
        elif ratio >= 0.75:
            return "encumbered", load, cap
        elif ratio >= 0.5:
            return "heavy_load", load, cap
        return "light_load", load, cap

    def get_penalties(self, condition):
        """Agility and speed penalties per condition."""
        return {
            "light_load": {},
            "heavy_load": {"agility": -1},
            "encumbered": {"agility": -2},
            "over_encumbered": {"agility": -3, "strength": -1},
        }.get(condition, {})

    def format_for_scene(self, entity_id):
        """Short string for scene assembler."""
        cond, load, cap = self.check_encumbrance(entity_id)
        if cond == "light_load":
            return ""
        return f"{cond} ({load:.1f}/{cap:.0f} kg)"
