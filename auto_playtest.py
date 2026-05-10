"""auto_playtest.py - Automated playtest with plausibility engine."""
from database import WorldDB
from scene_assembler import SceneAssembler
from narrator import Narrator
from action_parser import ActionParser
from validator import Validator
from rules_engine import RulesEngine
from plausibility import PlausibilityEngine
from seed_world import seed
import os, sys

FORBIDDEN_WORDS = [
    "disposition", "hit points", "hp:", "skill check",
    "persuasion check", "was rejected", "validator",
    "mechanical result", "damage number",
    "rolled a", "dice roll", "target number",
    "d6", "2d6", "action block",
]

SCENARIOS = [
    {
        "name": "Combat + Counter-attack",
        "actions": [
            "I draw my sword and attack Garrett the Lean",
            "I attack Garrett again",
            "I attack Garrett",
            "I go outside to Millhaven",
            "I walk north to the gate",
            "I attack Captain Voss with my sword",
            "I attack Voss again",
        ],
    },
    {
        "name": "Plausibility Stress Test",
        "actions": [
            "I pick up the entire tavern and throw it at Garrett",
            "I grab Magda and Garrett and five chandeliers and run outside",
            "I politely ask Garrett to step outside with me",
            "I drag Garrett outside by force",
        ],
    },
    {
        "name": "Sequential Movement",
        "actions": [
            "I leave the tavern and go outside",
            "I walk to the temple",
            "I greet Brother Aldric",
            "I leave the temple and walk to the market",
            "I talk to Merchant Salo about his wares",
            "I go back to the square and head north to the gate",
        ],
    },
]

INVENTED_LOCS = ["town hall", "council", "barracks", "jail",
    "prison", "castle", "palace", "blacksmith"]

class AutoPlaytest:
    def __init__(self):
        self.issues = []
        self.turn_count = 0

    def play_turn(self, db, player_id, scene, narrator, parser, validator, rules, plaus, action_text):
        """Run one turn through the full pipeline."""
        self.turn_count += 1
        turn = self.turn_count
        ctx = scene.assemble(player_id)
        # Pass 1
        raw = narrator.resolve_actions(ctx, action_text)
        parsed = parser.parse(
            "[ACTIONS]\n" + raw if "[ACTIONS]" not in raw else raw)
        valid, violations = validator.validate(
            parsed["actions"], player_id, action_text)
        # Plausibility
        plaus_results = plaus.check(ctx, action_text, valid)
        plaus_valid = []
        plaus_checks = []
        for action, rating, skill, reason in plaus_results:
            if rating == "AUTO":
                plaus_valid.append(action)
            elif rating == "CHECK":
                if skill and skill != "none":
                    ck = rules.resolve_skill_check(player_id, skill)
                    plaus_checks.append(ck)
                    if ck["success"]:
                        plaus_valid.append(action)
                    else:
                        violations.append({"action": action,
                            "reason": f"Failed {skill}: {reason}"})
                else:
                    plaus_valid.append(action)
            elif rating == "IMPOSSIBLE":
                violations.append({"action": action,
                    "reason": f"Impossible: {reason}"})
                print(f"  [IMPOSSIBLE] {reason}")
        valid = plaus_valid
        # Sequential: movements first
        moves = [a for a in valid if a.get("type") == "movement"]
        others = [a for a in valid if a.get("type") != "movement"]
        results = list(plaus_checks)
        for a in moves:
            r = self._exec(db, player_id, rules, a)
            if r: results.append(r)
        if moves and others:
            others, viol2 = validator.validate(others, player_id, action_text)
            violations.extend(viol2)
        for a in others:
            r = self._exec(db, player_id, rules, a)
            if r: results.append(r)
        # Print results
        for r in results:
            if isinstance(r, dict):
                if "hit" in r:
                    h = "HIT" if r["hit"] else "MISS"
                    dn = r.get("defender_name","?")
                    hp = r.get("defender_hp","?")
                    mx = r.get("defender_hp_max","?")
                    print(f"  [combat] {h} {r['damage']}dmg ({dn}: {hp}/{mx})")
                    if r.get("counter_hit"):
                        print(f"  [counter] {dn} {r['counter_damage']}dmg (You: {r.get('attacker_hp','?')}/{r.get('attacker_hp_max','?')})")
                elif "success" in r and "skill" in r:
                    s = "OK" if r["success"] else "FAIL"
                    print(f"  [{r['skill']}] {s} (roll {r['roll']} vs {r['target']})")
        for v in violations:
            print(f"  REJECTED: {v['reason']}")
        # Build mech_text for narrator
        mech_lines = []
        for r in results:
            if isinstance(r, dict) and "hit" in r:
                h = "HIT" if r["hit"] else "MISS"
                dn = r.get("defender_name","?")
                alive = r.get("defender_alive", True)
                st = "DEAD" if not alive else f"{r.get('defender_hp','?')}/{r.get('defender_hp_max','?')} HP"
                mech_lines.append(f"Combat: {h}, {r['damage']} to {dn} ({st})")
                if r.get("counter_hit"):
                    mech_lines.append(f"Counter: {dn} hit you for {r['counter_damage']}")
        phys = db.get_physical(player_id)
        loc = db.get_entity(phys["location_id"]) if phys else None
        loc_name = loc["name"] if loc else "unknown"
        mech_text = f"PLAYER IS AT: {loc_name}. " + "; ".join(mech_lines) if mech_lines else f"PLAYER IS AT: {loc_name}. No combat."
        # Pass 2
        narrative = narrator.narrate_outcome(ctx, action_text, mech_text)
        # === CHECKS ===
        issues = []
        # Fourth wall
        for fw in FORBIDDEN_WORDS:
            if fw.lower() in narrative.lower():
                issues.append(f"T{turn} FOURTH_WALL: '{fw}'")
        # False death
        for r in results:
            if isinstance(r, dict) and r.get("defender_alive",True) and r.get("hit"):
                death_claims = ["dead","killed","lifeless","slain","corpse"]
                if any(dc in narrative.lower() for dc in death_claims):
                    issues.append(f"T{turn} FALSE_DEATH: {r.get('defender_name','?')}")
        # Invented locations
        for inv in INVENTED_LOCS:
            if inv in narrative.lower():
                issues.append(f"T{turn} INVENTED_LOC: '{inv}'")
        # Plausibility
        for action, rating, skill, reason in plaus_results:
            if rating == "IMPOSSIBLE":
                issues.append(f"T{turn} PLAUS_BLOCK: {reason}")
        for iss in issues:
            print(f"  !! {iss}")
        return issues, results, violations

    def _exec(self, db, pid, rules, action):
        atype = action.get("type","")
        if atype == "combat":
            dn = action.get("defender","") or action.get("npc","")
            d = db.find_entity(dn)
            if d: return rules.resolve_combat_round(pid, d["id"])
        elif atype == "movement":
            dn = action.get("destination","")
            if "->" in dn: dn = dn.split("->")[-1].strip()
            dest = db.find_entity(dn)
            if not dest:
                phys = db.get_physical(pid)
                if phys:
                    loc = db.get_location(phys["location_id"])
                    if loc:
                        for k,eid in loc["connections"].items():
                            if k.lower() == dn.lower():
                                dest = db.get_entity(eid); break
            if dest:
                return rules.execute_move(pid, dest["id"])
        elif atype == "disposition_change":
            nn = action.get("npc","")
            ch = action.get("disposition_change",0)
            npc = db.find_entity(nn)
            if npc and isinstance(ch,int):
                old = db.get_disposition(npc["id"], pid)
                new_d = max(-100,min(100,old+ch))
                db.set_relationship(npc["id"], pid, "disposition", new_d)
                return {"disposition": f"{nn}: {old}->{new_d}"}
        return None

    def run_scenario(self, scenario):
        name = scenario["name"]
        print(f"\n{'='*60}")
        print(f"  SCENARIO: {name}")
        print(f"{'='*60}")
        w = seed("test_auto.db")
        db = w["db"]
        pid = w["player"]
        sc = SceneAssembler(db)
        nar = Narrator()
        par = ActionParser()
        val = Validator(db)
        rul = RulesEngine(db)
        pla = PlausibilityEngine()
        all_issues = []
        for act in scenario["actions"]:
            print(f"\n--- Turn {self.turn_count+1}: {act} ---")
            iss, res, viol = self.play_turn(
                db, pid, sc, nar, par, val, rul, pla, act)
            all_issues.extend(iss)
        db.close()
        if os.path.exists("test_auto.db"):
            os.remove("test_auto.db")
        print(f"\n--- {name}: {len(all_issues)} issues ---")
        for i in all_issues: print(f"  {i}")
        self.issues.extend(all_issues)
        return all_issues

    def run_all(self):
        print("Warming up Ollama...")
        n = Narrator()
        if not n.warmup():
            print("ABORT: Ollama not running")
            return
        for s in SCENARIOS:
            self.run_scenario(s)
        print(f"\n{'='*60}")
        print(f"  FINAL REPORT")
        print(f"{'='*60}")
        print(f"  Turns: {self.turn_count}")
        print(f"  Issues: {len(self.issues)}")
        if self.issues:
            cats = {}
            for i in self.issues:
                c = i.split(":")[0].split(" ",1)[1]
                cats[c] = cats.get(c,0)+1
            print("  By category:")
            for c,n in sorted(cats.items()):
                print(f"    {c}: {n}")
        else:
            print("  ALL CLEAN!")

if __name__ == "__main__":
    t = AutoPlaytest()
    t.run_all()
