"""plausibility.py - Common sense filter between actions and mechanics.
Judges whether the player can PHYSICALLY ATTEMPT an action.
Returns AUTO, CHECK (with skill), or IMPOSSIBLE for each action.

Phase 0 rewrite:
- Whitelist routes known action types without an LLM call
- All combat → CHECK unconditionally (combat system handles outcome)
- LLM prompt narrowed to physics/world-state only
- LLM never judges NPC reactions or social consequences
"""
import requests
import json

PLAUSIBILITY_PROMPT = """You are the PHYSICS FILTER for a text RPG.
You judge ONLY whether the player can physically attempt each action.

RULES:
- You judge the PLAYER'S ACTION ONLY.
- You do NOT judge NPC reactions, social consequences, or whether the action is smart.
- You do NOT imagine what NPCs would do in response.
- You do NOT consider whether NPCs would "allow" or "prevent" the action.
- If the player has the body, the location, and the means, the action is possible.

RATINGS:
- AUTO: Physically trivial, needs no check. Walking, talking, picking up an object, looking around, drawing a weapon, opening an unlocked door.
- CHECK: Physically possible but needs skill or luck. Specify which skill. Climbing a wall, picking a lock, sneaking past someone, persuading someone, lifting something very heavy, leaping a gap.
- IMPOSSIBLE: Violates physics or world state. Flying without wings, interacting with someone not present, using an item the player doesn't have, walking through walls, moving to an unconnected location.

IMPORTANT:
- Attacks and combat are NEVER judged here. If you see a combat action, skip it.
- Leaving a location is ALWAYS AUTO regardless of social situation (unpaid tabs, ongoing conversations, etc.)
- Talking to someone present is ALWAYS AUTO. The content of speech doesn't matter.
- You are a physics referee, not a social referee.

For EACH action, respond with exactly one line:
ACTION_NUMBER: RATING | SKILL | REASON

Respond ONLY with numbered lines. No other text."""

# ── Whitelist: these action types skip the LLM entirely ──────────

_WHITELIST = {
    # type → (rating, skill, reason)
    "combat":             ("AUTO",  "none",     "combat resolved by combat system"),
    "movement":           ("AUTO",  "none",     "movement to connected location"),
    "dialogue":           ("AUTO",  "none",     "talking to present NPC"),
    "disposition_change": ("AUTO",  "none",     "social reaction"),
    "look":               ("AUTO",  "none",     "observing surroundings"),
    "examine":            ("AUTO",  "none",     "examining something present"),
    "equip":              ("AUTO",  "none",     "equipping owned item"),
    "unequip":            ("AUTO",  "none",     "unequipping item"),
    "pickup":             ("AUTO",  "none",     "picking up accessible item"),
    "drop":               ("AUTO",  "none",     "dropping held item"),
    "use_item":           ("AUTO",  "none",     "using an item"),
}


class PlausibilityEngine:
    def __init__(self, model="gemma3:12b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def check(self, scene_context, player_input, actions):
        """Check plausibility of each action.
        Returns list of (action, rating, skill, reason) tuples."""
        if not actions:
            return []

        whitelisted = []
        need_llm = []

        for i, a in enumerate(actions):
            atype = a.get("type", "").lower().strip()
            if atype in _WHITELIST:
                rating, skill, reason = _WHITELIST[atype]
                whitelisted.append((i, a, rating, skill, reason))
            else:
                need_llm.append((i, a))

        # If everything was whitelisted, skip LLM entirely
        if not need_llm:
            return [(a, r, s, rsn) for (_, a, r, s, rsn) in whitelisted]

        # Call LLM only for unknown/ambiguous action types
        llm_results = self._llm_check(scene_context, player_input, need_llm)

        # Merge whitelisted + LLM results in original order
        all_results = {}
        for (idx, a, r, s, rsn) in whitelisted:
            all_results[idx] = (a, r, s, rsn)
        for (idx, result) in llm_results:
            all_results[idx] = result

        return [all_results[i] for i in sorted(all_results.keys())]

    def _llm_check(self, scene_context, player_input, indexed_actions):
        """Call LLM for actions that weren't whitelisted.
        indexed_actions: list of (original_index, action_dict)
        Returns list of (original_index, (action, rating, skill, reason))"""
        # Renumber for the LLM prompt (1-based)
        action_lines = []
        for llm_num, (orig_idx, a) in enumerate(indexed_actions, 1):
            parts = [f"{k}: {v}" for k, v in a.items()]
            action_lines.append(f"  {llm_num}. {', '.join(parts)}")
        actions_text = "\n".join(action_lines)

        prompt = f"""{scene_context}

=== PLAYER SAID ===
{player_input}

=== PROPOSED ACTIONS (judge these) ===
{actions_text}

Judge each action's PHYSICAL POSSIBILITY only. One line per action."""

        messages = [
            {"role": "system", "content": PLAUSIBILITY_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            r = requests.post(f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages,
                      "stream": False}, timeout=None)
            r.raise_for_status()
            raw = r.json()["message"]["content"]
            parsed = self._parse_response(raw, indexed_actions)
            return parsed
        except Exception as e:
            # Fail open: default to AUTO
            return [(idx, (a, "AUTO", "none", f"plausibility error: {e}"))
                    for idx, a in indexed_actions]

    def _parse_response(self, raw, indexed_actions):
        """Parse LLM response into structured results.
        Returns list of (original_index, (action, rating, skill, reason))"""
        results = []
        lines = raw.strip().split("\n")

        for llm_num, (orig_idx, action) in enumerate(indexed_actions, 1):
            rating = "AUTO"
            skill = "none"
            reason = ""
            for line in lines:
                line = line.strip()
                if line.startswith(f"{llm_num}:") or line.startswith(f"{llm_num}."):
                    parts = line.split("|")
                    if len(parts) >= 2:
                        rtext = parts[0].split(":", 1)[-1].strip().upper()
                        if "IMPOSSIBLE" in rtext:
                            rating = "IMPOSSIBLE"
                        elif "CHECK" in rtext:
                            rating = "CHECK"
                        else:
                            rating = "AUTO"
                        skill = parts[1].strip().lower() if len(parts) > 1 else "none"
                        reason = parts[2].strip() if len(parts) > 2 else ""
                    break
            results.append((orig_idx, (action, rating, skill, reason)))
        return results

    def format_debug(self, results):
        """Format plausibility results for debug display."""
        lines = []
        for action, rating, skill, reason in results:
            atype = action.get("type", "?")
            npc = action.get("npc", "") or action.get("defender", "")
            tag = f"{atype}"
            if npc:
                tag += f"({npc})"
            if rating == "AUTO":
                lines.append(f"  [plaus] {tag}: AUTO")
            elif rating == "CHECK":
                lines.append(f"  [plaus] {tag}: CHECK({skill}) - {reason}")
            elif rating == "IMPOSSIBLE":
                lines.append(f"  [plaus] {tag}: IMPOSSIBLE - {reason}")
        return "\n".join(lines)
