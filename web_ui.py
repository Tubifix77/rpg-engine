"""web_ui.py - Flask web UI for RPG Engine."""
from flask import Flask, render_template, request, jsonify
from narrator import Narrator, NARRATE_PROMPT
from action_parser import ActionParser
from validator import Validator
from rules_engine import RulesEngine
from plausibility import PlausibilityEngine
from scene_assembler import SceneAssembler
from seed_world import seed
from encumbrance import EncumbranceSystem
from survival import SurvivalSystem
from economy import EconomySystem
from songs import SongSystem
from disturbance import DisturbanceSystem
from dissonance import DissonanceSystem
from database import WorldDB
import json, os

app = Flask(__name__)
G = {}

def init_game(model="gemma3:12b"):
    w = seed("world.db")
    G["db"] = w["db"]
    G["pid"] = w["player"]
    G["sc"] = SceneAssembler(G["db"])
    G["nar"] = Narrator(model=model)
    G["par"] = ActionParser()
    G["val"] = Validator(G["db"])
    G["rul"] = RulesEngine(G["db"])
    G["pla"] = PlausibilityEngine(model=model)
    G["enc"] = EncumbranceSystem(G["db"])
    G["surv"] = SurvivalSystem(G["db"])
    G["econ"] = EconomySystem(G["db"])
    G["songs"] = SongSystem(G["db"])
    G["disturb"] = DisturbanceSystem(G["db"])
    G["diss"] = DissonanceSystem(G["db"])
    G["hist"] = []
    G["last_mech"] = ""
    G["nar"].warmup()

def get_npc_info(db, pid, loc_id):
    npcs = db.get_entities_at(loc_id, "npc")
    info = []
    for n in npcs:
        np = db.get_physical(n["id"])
        disp = db.get_disposition(n["id"], pid)
        goals = db.get_goals(n["id"])
        nk = db.get_knowledge(n["id"])
        mood = "hostile" if disp < -20 else "wary" if disp < 0 else "neutral" if disp < 20 else "friendly"
        info.append({"name": n["name"], "notes": n.get("notes",""),
            "hp": np["hp_current"], "hp_max": np["hp_max"],
            "alive": bool(np["is_alive"]),
            "disposition": disp, "mood": mood,
            "goals": [g["description"] for g in goals],
            "knows": [k["content"] for k in nk]})
    return info

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/state")
def api_state():
    db, pid = G["db"], G["pid"]
    player = db.get_entity(pid)
    phys = db.get_physical(pid)
    stats = db.get_stats(pid)
    inv = db.get_inventory(pid)
    clock = db.get_clock()
    loc_id = phys["location_id"]
    loc = db.get_entity(loc_id)
    loc_d = db.get_location(loc_id)
    knowledge = db.get_knowledge(pid)
    return jsonify({
        "player": {"name": player["name"],
            "hp": phys["hp_current"], "hp_max": phys["hp_max"],
            "str": stats["strength"], "agi": stats["agility"],
            "int": stats["intelligence"], "pre": stats["precision"],
            "wil": stats["will"], "per": stats["perception"], "skills": stats["skills"],
            "conds": json.loads(phys["conditions"] or "[]"),
            "inv": inv, "notes": player.get("notes",""),
            "knowledge": [k["content"] for k in knowledge],
            "silver": db.get_currency(pid),
            "encumbrance": G["enc"].check_encumbrance(pid),
            "survival": db.get_survival(pid)},
        "location": {"name": loc["name"], "desc": loc_d["description"],
            "state": loc_d.get("current_state",""),
            "exits": list(loc_d["connections"].keys())},
        "npcs": get_npc_info(db, pid, loc_id),
        "clock": dict(clock) if clock else {},
        "history": G["hist"][-20:]})

def _resolve_destination(db, pid, raw_dest):
    """Fuzzy match a destination string to a connected location entity."""
    if not raw_dest:
        return None
    dn = raw_dest.strip().lower()
    if "->" in dn:
        dn = dn.split("->")[-1].strip()
    # Remove common filler words
    for w in ["the ", "to ", "towards ", "toward ", "into ", "go "]:
        if dn.startswith(w):
            dn = dn[len(w):]
    phys = db.get_physical(pid)
    if not phys:
        return None
    loc = db.get_location(phys["location_id"])
    if not loc:
        return None
    conns = loc["connections"]  # {"outside": eid, "cellar": eid, ...}

    # Build lookup: key -> eid, location_name -> eid
    key_map = {}  # lowercase key/name -> entity_id
    for k, eid in conns.items():
        key_map[k.lower()] = eid
        e = db.get_entity(eid)
        if e:
            key_map[e["name"].lower()] = eid

    # 1. Exact match on key or location name
    if dn in key_map:
        return db.get_entity(key_map[dn])

    # 2. Partial match: destination contains key or key contains destination
    for k, eid in key_map.items():
        if dn in k or k in dn:
            return db.get_entity(eid)

    # 3. Synonym matching for common movement words
    EXIT_WORDS = {"outside", "out", "exit", "leave", "door", "street", "away"}
    if dn in EXIT_WORDS or any(w in dn for w in EXIT_WORDS):
        for k in ["outside", "out", "exit", "door", "street"]:
            if k in key_map:
                return db.get_entity(key_map[k])
        # If no explicit exit key, try first non-interior connection
        for k, eid in conns.items():
            if k.lower() not in {"cellar", "upstairs", "basement", "back_room"}:
                return db.get_entity(eid)

    # 4. Try global entity search (handles "Rusty Flagon", "North Gate" etc)
    found = db.find_entity(raw_dest)
    if found and found["id"] in conns.values():
        return found

    # 5. Nothing matched
    return None


def _exec_action(db, pid, rules, a):
    t = a.get("type","")
    if t == "combat":
        dn = a.get("defender","") or a.get("npc","")
        d = db.find_entity(dn)
        if d: return rules.resolve_combat_round(pid, d["id"])
    elif t == "song":
        sn = a.get("song_name", "") or a.get("song", "")
        rm = a.get("realm", "corporeal")
        tid = None
        tn = a.get("target", "") or a.get("npc", "")
        if tn:
            te = db.find_entity(tn)
            if te: tid = te["id"]
        return G["songs"].resolve_song(pid, sn, rm, tid)
    elif t == "movement":
        dn = a.get("destination","")
        dest = _resolve_destination(db, pid, dn)
        if dest: return rules.execute_move(pid, dest["id"])
    elif t == "disposition_change":
        nn = a.get("npc","")
        ch = a.get("disposition_change", 0)
        npc = db.find_entity(nn)
        if npc and isinstance(ch, int):
            old = db.get_disposition(npc["id"], pid)
            nv = max(-100, min(100, old + ch))
            db.set_relationship(npc["id"], pid, "disposition", nv)
            return {"disposition": f"{nn}: {old}->{nv}"}
    return None

@app.route("/api/action", methods=["POST"])
def api_action():
    db, pid = G["db"], G["pid"]
    act = request.json.get("action", "")
    if not act: return jsonify({"error": "empty"})
    ctx = G["sc"].assemble(pid)
    # Pass 1: actions
    raw = G["nar"].resolve_actions(ctx, act)
    parsed = G["par"].parse("[ACTIONS]\n" + raw if "[ACTIONS]" not in raw else raw)
    valid, viols = G["val"].validate(parsed["actions"], pid, act)
    # Plausibility
    pr = G["pla"].check(ctx, act, valid)
    pv, pi, results = [], [], []
    for action, rating, skill, reason in pr:
        pi.append({"type": action.get("type",""), "rating": rating, "reason": reason})
        if rating == "AUTO": pv.append(action)
        elif rating == "CHECK":
            if skill and skill != "none":
                ck = G["rul"].resolve_skill_check(pid, skill)
                results.append(ck)
                if ck["success"]: pv.append(action)
                else: viols.append({"action": action, "reason": f"Failed {skill}: {reason}"})
            else: pv.append(action)
        elif rating == "IMPOSSIBLE":
            viols.append({"action": action, "reason": f"Impossible: {reason}"})
    valid = pv
    # Sequential: moves first
    mvs = [a for a in valid if a.get("type") == "movement"]
    oth = [a for a in valid if a.get("type") != "movement"]
    for a in mvs:
        r = _exec_action(db, pid, G["rul"], a)
        if r: results.append(r)
    if mvs and oth:
        oth, v2 = G["val"].validate(oth, pid, act)
        viols.extend(v2)
    for a in oth:
        r = _exec_action(db, pid, G["rul"], a)
        if r: results.append(r)
    # Build mech text
    ml = []
    for r in results:
        if isinstance(r, dict) and "hit" in r:
            h = "HIT" if r["hit"] else "MISS"
            dn = r.get("defender_name","?")
            alive = r.get("defender_alive", True)
            st = "DEAD" if not alive else f"{r.get('defender_hp','?')}/{r.get('defender_hp_max','?')}"
            arm_txt = f" (armor absorbed {r.get('armor_absorbed', 0)})" if r.get('armor_absorbed', 0) > 0 else ""
            ml.append(f"Combat: {h}, {r['damage']} to {dn}{arm_txt} ({st})")
            if r.get("counter_hit"):
                ml.append(f"Counter: {dn} {r['counter_damage']}dmg back")
            if r.get("defender_flees"):
                ml.append(f"Morale: {dn} flees!")
        elif a.get("type") == "song" and r:
            ml.append(G["songs"].format_result(r))
            if r.get("disturbance", 0) > 0:
                phys = db.get_physical(pid)
                if phys:
                    dets = G["disturb"].check_detection(pid, phys["location_id"], r["disturbance"])
                    ml.append(G["disturb"].format_detections(dets))
    phys = db.get_physical(pid)
    loc = db.get_entity(phys["location_id"]) if phys else None
    ln = loc["name"] if loc else "?"
    mt = f"PLAYER IS AT: {ln}. " + "; ".join(ml) if ml else f"PLAYER IS AT: {ln}."
    nar_ml = list(ml)
    for v in viols:
        nar_ml.append('REJECTED: ' + v['reason'])
    mt = f"PLAYER IS AT: {ln}. " + "; ".join(nar_ml) if nar_ml else f"PLAYER IS AT: {ln}."
    G["last_mech"] = mt
    # Pass 2: narrate (blocking for web)
    narrative = G["nar"].narrate_outcome(ctx, act, mt, stream=False)
    # Strip streaming artifacts if any
    # Build history entry
    entry = {"action": act, "narrative": narrative,
        "mechanics": ml, "violations": [v["reason"] for v in viols],
        "plausibility": pi}
    G["hist"].append(entry)
    return jsonify(entry)

@app.route("/api/swipe", methods=["POST"])
def api_swipe():
    """Re-roll narration keeping mechanics fixed."""
    if not G["hist"]:
        return jsonify({"error": "No history"})
    db, pid = G["db"], G["pid"]
    ctx = G["sc"].assemble(pid)
    last = G["hist"][-1]
    mt = G["last_mech"]
    narrative = G["nar"].narrate_outcome(ctx, last["action"], mt, stream=False)
    last["narrative"] = narrative
    last["swiped"] = True
    return jsonify(last)

if __name__ == "__main__":
    init_game()
    app.run(debug=False, port=5000)
