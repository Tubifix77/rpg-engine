"""action_parser.py - Extract structured actions from LLM output."""
import re

class ActionParser:
    def parse(self, llm_output):
        """Parse LLM output into narrative + actions."""
        narrative = ""
        actions = []
        # Split on [NARRATIVE] and [ACTIONS]
        parts = re.split(r'\[NARRATIVE\]|\[ACTIONS\]', llm_output, flags=re.IGNORECASE)
        if len(parts) >= 3:
            narrative = parts[1].strip()
            actions_text = parts[2].strip()
        elif len(parts) == 2:
            # Maybe only narrative or only actions
            if re.search(r'\[NARRATIVE\]', llm_output, re.IGNORECASE):
                narrative = parts[1].strip()
                actions_text = ""
            else:
                narrative = parts[0].strip()
                actions_text = parts[1].strip()
        else:
            # No markers at all - treat entire output as narrative
            narrative = llm_output.strip()
            actions_text = ""
        if actions_text:
            actions = self._parse_actions(actions_text)
        return {
            "narrative": narrative,
            "actions": actions,
            "has_actions": len(actions) > 0,
            "raw": llm_output,
        }

    def _parse_actions(self, text):
        """Parse key:value action lines into a list of action dicts."""
        actions = []
        current = {}
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                if current:
                    actions.append(current)
                    current = {}
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                val = val.strip()
                # Try to parse numeric values
                try:
                    val = int(val)
                except ValueError:
                    try:
                        val = float(val)
                    except ValueError:
                        pass
                current[key] = val
        if current:
            actions.append(current)
        for a in actions:
            if "skill_name" in a and "skill_check_needed" not in a:
                a["skill_check_needed"] = a.pop("skill_name")
            if "target_number" in a and "skill_check_needed" in a:
                sc = a["skill_check_needed"]
                tn = a.pop("target_number")
                if isinstance(sc, str):
                    a["skill_check_needed"] = f"{sc} {tn}"
            if a.get("type") == "combat" and "defender" not in a and "npc" in a:
                a["defender"] = a["npc"]
        return actions

    def needs_reprompt(self, parsed):
        """Check if we need to ask LLM to try again."""
        return not parsed["has_actions"]

if __name__ == "__main__":
    ap = ActionParser()
    # Test 1: Full proper output
    test1 = """
[NARRATIVE]
The guard eyes you suspiciously. "No one enters after dark," he growls.

[ACTIONS]
type: dialogue
npc: guard_north_gate
disposition_change: -5
knowledge_gained: guard knows player wants entry
skill_check_needed: persuasion target 8
"""
    r = ap.parse(test1)
    print("=== Test 1: Full output ===")
    print(f"Narrative: {r['narrative'][:50]}...")
    print(f"Actions: {r['actions']}")
    print(f"Needs reprompt: {ap.needs_reprompt(r)}")
    # Test 2: No actions block
    test2 = "The barkeeper smiles warmly."
    r = ap.parse(test2)
    print("\n=== Test 2: No actions ===")
    print(f"Narrative: {r['narrative']}")
    print(f"Needs reprompt: {ap.needs_reprompt(r)}")
    # Test 3: Multiple action blocks
    test3 = """
[NARRATIVE]
You trade blows with the bandit.

[ACTIONS]
type: combat
attacker: player
defender: bandit
skill_check_needed: fighting

type: disposition_change
npc: barkeeper
disposition_change: 5
reason: impressed by bravery
"""
    r = ap.parse(test3)
    print("\n=== Test 3: Multiple actions ===")
    print(f"Actions count: {len(r['actions'])}")
    for a in r["actions"]:
        print(f"  {a}")
    print("\nAll parser tests done.")
