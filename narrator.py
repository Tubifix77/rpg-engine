"""narrator.py - Two-pass LLM narrator via Ollama.
Pass 1: Determine actions (fast, no streaming)
Pass 2: Narrate outcome grounded in mechanical results (streaming)"""
import requests
import json
import sys

ACTIONS_PROMPT = """You are the rules interpreter for a text-based RPG.
Given the scene and the player's action, determine what mechanical game actions should occur.

RULES:
1. Respond ONLY with an [ACTIONS] block. NO narrative, NO prose.
2. Use key: value format, one per line:
   type: dialogue / combat / movement / item_use / disposition_change / skill_check
   npc: name of NPC involved (MUST be from NPCs PRESENT list)
   disposition_change: number (-30 to +30)
   skill_check_needed: skill_name
   destination: location name (for movement)
   item: item name (for item_use)
3. Multiple actions: separate with a blank line
4. ONLY use NPC names from the NPCs PRESENT section
5. ANY name not in NPCs PRESENT will be REJECTED
6. NEVER propose movement unless the player says they go somewhere
7. If the player does BOTH movement AND an NPC interaction, emit them as SEPARATE actions with a blank line between.
   Movement FIRST, then the NPC action. Example:
   type: movement
   destination: outside

   type: dialogue
   npc: Garrett the Lean
8. NEVER propose item_use unless the player says they use an item
9. NEVER put the player character as npc target
"""

NARRATE_PROMPT = """You are the Game Master narrator for a text-based RPG.
You will be given the scene context, what the player tried to do, and the MECHANICAL RESULTS of what actually happened (dice rolls, damage, etc).

RULES:
1. Narrate ONLY what the mechanical results support.
2. If an attack HIT and dealt damage, describe the wound. If it MISSED, describe the dodge or parry.
3. If the target DIED (HP reached 0), you may describe their death.
4. If the target is ALIVE, do NOT describe them dying or being killed.
5. If movement was REJECTED, the player did NOT move.
   The player STAYS at the location shown in PLAYER IS CURRENTLY AT.
   Do NOT describe them arriving anywhere else. Describe them remaining where they are.
6. Always check PLAYER IS CURRENTLY AT and narrate from that location.
7. Keep narrative vivid but concise (2-4 paragraphs).
8. Voice NPCs in character based on their disposition.
9. NEVER invent NPCs, items, or locations not in the scene context.
10. Respond with prose only. No [ACTIONS] block, no tags.
11. NEVER reference game mechanics in the narrative. No mention of:
    - hit points, HP, damage numbers, dice rolls
    - skill checks, persuasion checks, success/failure of checks
    - disposition values or changes
    - "rejected", "validator", "mechanical results"
    - any game system terminology
    Characters should NEVER know about or mention the game system.
12. NPCs may reference ONLY locations and NPCs from the WORLD LOCATIONS and ALL LIVING NPCs lists.
13. NPCs must NOT invent rules, permissions, fees, councils, or requirements that are not in the scene context.
14. Unnamed background people (crowds, children, dogs) are fine as atmosphere but they cannot create quests, give keys, block paths, or change game state.
    Show results through actions and reactions, not numbers.
"""

class Narrator:
    def __init__(self, model="gemma3:12b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.history = []

    def warmup(self):
        """Load model into VRAM."""
        print("Warming up narrator (loading model into GPU)...", end="", flush=True)
        try:
            r = requests.post(f"{self.base_url}/api/chat",
                json={"model": self.model,
                      "messages": [{"role": "user", "content": "Reply: Initialized"}],
                      "stream": False}, timeout=300)
            r.raise_for_status()
            print(" ready!")
            return True
        except requests.exceptions.ConnectionError:
            print(" FAILED (Ollama not running)")
            return False
        except Exception as e:
            print(f" FAILED ({e})")
            return False

    def resolve_actions(self, scene_context, player_action):
        """Pass 1: Determine mechanical actions. Fast, no streaming."""
        prompt = f"""{scene_context}

=== PLAYER ACTION ===
{player_action}

Respond with ONLY an [ACTIONS] block. No narrative."""
        messages = [
            {"role": "system", "content": ACTIONS_PROMPT},
        ]
        for h in self.history[-4:]:
            messages.append(h)
        messages.append({"role": "user", "content": prompt})
        return self._call_blocking(messages)

    def narrate_outcome(self, scene_context, player_action, mech_results):
        """Pass 2: Narrate grounded in mechanical results. Streaming."""
        prompt = f"""{scene_context}

=== PLAYER ACTION ===
{player_action}

=== MECHANICAL RESULTS (what actually happened) ===
{mech_results}

Narrate what happened based on the mechanical results above."""
        messages = [
            {"role": "system", "content": NARRATE_PROMPT},
        ]
        for h in self.history[-4:]:
            messages.append(h)
        messages.append({"role": "user", "content": prompt})
        response = self._call_stream(messages)
        self.history.append({"role": "user", "content": player_action})
        self.history.append({"role": "assistant", "content": response})
        return response

    def _call_blocking(self, messages):
        """Non-streaming call for actions pass."""
        try:
            r = requests.post(f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages,
                      "stream": False}, timeout=None)
            r.raise_for_status()
            return r.json()["message"]["content"]
        except requests.exceptions.ConnectionError:
            return "[ACTIONS]\ntype: system_error\nerror: ollama_not_running"
        except Exception as e:
            return f"[ACTIONS]\ntype: system_error\nerror: {e}"

    def _call_stream(self, messages):
        """Stream tokens to stdout. Returns full text."""
        full = []
        try:
            r = requests.post(f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": True},
                stream=True, timeout=None)
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                full.append(token)
                sys.stdout.write(token)
                sys.stdout.flush()
                if data.get("done"):
                    break
            print()
            return "".join(full)
        except requests.exceptions.ConnectionError:
            print("(Ollama not running)")
            return "The narrator falls silent."
        except Exception as e:
            print(f"(Error: {e})")
            return f"The narrator stumbles. ({e})"

    def clear_history(self):
        self.history = []

    def summarize_for_log(self, scene_text):
        messages = [
            {"role": "system", "content": "Summarize in one sentence, narrator voice."},
            {"role": "user", "content": scene_text},
        ]
        return self._call_blocking(messages)
