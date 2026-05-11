"""dice.py - d666 resolution system.
Roll 2d6 vs target, 3rd d6 = check digit.
111 = Divine Intervention, 666 = Infernal."""
import random


def roll_d666():
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    d3 = random.randint(1, 6)
    intervention = None
    if d1 == 1 and d2 == 1 and d3 == 1:
        intervention = "divine"
    elif d1 == 6 and d2 == 6 and d3 == 6:
        intervention = "infernal"
    return d1, d2, d3, d1 + d2, d3, intervention


def skill_check(stat, skill_rank, modifier=0):
    target = stat + skill_rank + modifier
    d1, d2, d3, total, check_digit, intervention = roll_d666()
    if intervention == "divine":
        success = True
        check_digit = 6
    elif intervention == "infernal":
        success = False
        check_digit = 6
    else:
        success = total <= target
    return {
        "success": success,
        "check_digit": check_digit,
        "intervention": intervention,
        "roll": total,
        "dice": (d1, d2, d3),
        "target": target,
    }


def contested_check(stat_a, skill_a, stat_b, skill_b):
    r_a = skill_check(stat_a, skill_a)
    r_b = skill_check(stat_b, skill_b)
    if r_a["intervention"] == "divine":
        winner = "a"
    elif r_b["intervention"] == "divine":
        winner = "b"
    elif r_a["intervention"] == "infernal":
        winner = "b"
    elif r_b["intervention"] == "infernal":
        winner = "a"
    elif r_a["success"] and not r_b["success"]:
        winner = "a"
    elif r_b["success"] and not r_a["success"]:
        winner = "b"
    elif r_a["success"] and r_b["success"]:
        if r_a["check_digit"] > r_b["check_digit"]:
            winner = "a"
        elif r_b["check_digit"] > r_a["check_digit"]:
            winner = "b"
        else:
            winner = "tie"
    else:
        winner = "tie"
    return {"winner": winner, "roll_a": r_a, "roll_b": r_b}


def initiative_roll(agility):
    return agility + random.randint(1, 6)


def damage_roll(weapon_base, check_digit, str_modifier=0, armor=0):
    return max(0, weapon_base + check_digit + str_modifier - armor)


if __name__ == "__main__":
    print("=== d666 Dice Tests ===")
    random.seed(42)
    r = skill_check(4, 2)
    print(f"Skill(4+2=6): roll={r['roll']} cd={r['check_digit']} ok={r['success']}")
    r = contested_check(4, 2, 3, 1)
    print(f"Contested: winner={r['winner']}")
    print(f"  Damage(base=3,cd=4,str=1,arm=2): {damage_roll(3, 4, 1, 2)}")
    print("All dice tests done.")
