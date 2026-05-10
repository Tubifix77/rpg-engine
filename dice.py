"""dice.py - Resolution mechanics. Pure deterministic, no LLM."""
import random

def roll_2d6():
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    return d1, d2, d1 + d2

def skill_check(stat, skill_rank, modifier=0):
    """Roll 2d6 vs target (stat + skill + mod).
    Returns (success, margin, crit, roll, target)."""
    target = stat + skill_rank + modifier
    d1, d2, total = roll_2d6()
    crit = None
    if total == 2:
        crit = "critical_success"
    elif total == 12:
        crit = "critical_failure"
    success = total <= target
    margin = target - total if success else total - target
    if crit == "critical_success":
        success = True
        margin = max(margin, 5)
    elif crit == "critical_failure":
        success = False
        margin = max(margin, 5)
    return {
        "success": success,
        "margin": margin,
        "crit": crit,
        "roll": total,
        "dice": (d1, d2),
        "target": target,
    }

def contested_check(stat_a, skill_a, stat_b, skill_b):
    """Both sides roll, higher margin wins."""
    r_a = skill_check(stat_a, skill_a)
    r_b = skill_check(stat_b, skill_b)
    if r_a["crit"] == "critical_success" and r_b["crit"] != "critical_success":
        winner = "a"
    elif r_b["crit"] == "critical_success" and r_a["crit"] != "critical_success":
        winner = "b"
    elif r_a["success"] and not r_b["success"]:
        winner = "a"
    elif r_b["success"] and not r_a["success"]:
        winner = "b"
    elif r_a["margin"] > r_b["margin"]:
        winner = "a"
    elif r_b["margin"] > r_a["margin"]:
        winner = "b"
    else:
        winner = "tie"
    return {"winner": winner, "roll_a": r_a, "roll_b": r_b}

def initiative_roll(ethereal):
    return ethereal + random.randint(1, 6)

def damage_roll(weapon_base, margin):
    return max(1, weapon_base + margin)

if __name__ == "__main__":
    print("=== Dice Tests ===")
    random.seed(42)
    r = skill_check(4, 2)
    print(f"Skill check (4+2=6): roll={r['roll']} target={r['target']} success={r['success']} margin={r['margin']}")
    r = contested_check(4, 2, 3, 1)
    print(f"Contested: winner={r['winner']} A:{r['roll_a']['roll']} B:{r['roll_b']['roll']}")
    for _ in range(5):
        i = initiative_roll(3)
        print(f"Initiative(eth=3): {i}")
    print(f"Damage(base=3, margin=2): {damage_roll(3, 2)}")
    print("All dice tests done.")
