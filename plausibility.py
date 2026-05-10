"""plausibility.py - Common sense filter between actions and mechanics.
Asks LLM: is this physically/socially reasonable?
Returns AUTO, CHECK (with skill), or IMPOSSIBLE for each action."""
import requests
import json

PLAUSIBILITY_PROMPT = """You are the common sense filter for a text RPG.
Given a scene and proposed actions, judge each action's plausibility.

For EACH action, respond with exactly one line:
ACTION_NUMBER: RATING | SKILL | REASON

RATING is one of:
- AUTO: Trivially possible, no check needed (walking, talking, picking up a mug)
- CHECK: Possible but requires a skill check. Specify which skill.
- IMPOSSIBLE: Cannot physically happen. Explain briefly why.

Examples:
1: AUTO | none | Walking to a nearby location
2: CHECK | fighting | Dragging an unwilling armed guard
3: IMPOSSIBLE | none | Carrying a horse on your back
4: CHECK | persuasion | Convincing a hostile NPC to follow you
5: AUTO | none | Drawing your sword
6: IMPOSSIBLE | none | Lifting five chandeliers at once
7: CHECK | stealth | Sneaking past a guard unnoticed

Be strict about physical reality. One person cannot:
- Carry more than one unconscious body
- Lift anything heavier than themselves
- Be in two places at once
- Force multiple unwilling people simultaneously
- Perform superhuman feats

Be lenient about social actions. People CAN:
- Try to persuade (even if likely to fail)
- Bluff or lie (with a check)
- Intimidate (with a check)
- Attempt risky physical actions (climbing, jumping) with a check

Respond ONLY with numbered lines. No other text."""

class PlausibilityEngine:
    def __init__(self, model="gemma3:12b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def check(self, scene_context, player_input, actions):
        """Check plausibility of each action.
        Returns list of (action, rating, skill, reason) tuples."""
        if not actions:
            return []
        # Format actions for the prompt
        action_lines = []
        for i, a in enumerate(actions):
            parts = [f"{k}: {v}" for k, v in a.items()]
            action_lines.append(f"  {i+1}. {', '.join(parts)}")
        actions_text = "\n".join(action_lines)
        prompt = f"""{scene_context}

=== PLAYER SAID ===
{player_input}

=== PROPOSED ACTIONS ===
{actions_text}

Judge each action. One line per action."""
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
            return self._parse_response(raw, actions)
        except Exception as e:
            # On error, default to AUTO for all (fail open)
            return [(a, "AUTO", "none", f"plausibility error: {e}") for a in actions]

    def _parse_response(self, raw, actions):
        """Parse LLM response into structured results."""
        results = []
        lines = raw.strip().split("\n")
        for i, action in enumerate(actions):
            rating = "AUTO"
            skill = "none"
            reason = ""
            # Try to find matching line
            for line in lines:
                line = line.strip()
                if line.startswith(f"{i+1}:") or line.startswith(f"{i+1}."):
                    parts = line.split("|")
                    if len(parts) >= 2:
                        # Extract rating
                        rtext = parts[0].split(":",1)[-1].strip().upper()
                        if "IMPOSSIBLE" in rtext:
                            rating = "IMPOSSIBLE"
                        elif "CHECK" in rtext:
                            rating = "CHECK"
                        else:
                            rating = "AUTO"
                        skill = parts[1].strip().lower() if len(parts) > 1 else "none"
                        reason = parts[2].strip() if len(parts) > 2 else ""
                    break
            results.append((action, rating, skill, reason))
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
