"""seed_world.py - Millhaven scenario: expanded world."""
from database import WorldDB
import os

def seed(db_path="world.db"):
    if os.path.exists(db_path):
        os.remove(db_path)
    db = WorldDB(db_path)

    # === LOCATIONS (15) ===
    town = db.create_entity("location", "Millhaven", "day 1",
        "A small farming town at a river crossing")
    tavern = db.create_entity("location", "The Rusty Flagon", "day 1")
    gate = db.create_entity("location", "North Gate", "day 1")
    market = db.create_entity("location", "Market Square", "day 1")
    temple = db.create_entity("location", "Temple of the Dawn", "day 1")
    cellar = db.create_entity("location", "Tavern Cellar", "day 1")
    road = db.create_entity("location", "North Road", "day 1")
    mayor_house = db.create_entity("location", "Mayor's House", "day 1")
    river = db.create_entity("location", "River Crossing", "day 1")
    south_gate = db.create_entity("location", "South Gate", "day 1")
    farm = db.create_entity("location", "Burned Farmstead", "day 1")
    south_road = db.create_entity("location", "South Road", "day 1")
    forest = db.create_entity("location", "Dark Forest", "day 1")
    bandit_camp = db.create_entity("location", "Bandit Camp", "day 1")
    well = db.create_entity("location", "Town Well", "day 1")
    stable = db.create_entity("location", "Stables", "day 1")

    # === LOCATION CONNECTIONS ===
    # Town square is the hub
    db.set_location(town, None,
        "The town square of Millhaven, muddy streets radiate outward",
        "A festival banner hangs torn from last year",
        {"tavern": tavern, "market": market, "temple": temple,
         "north_gate": gate, "south_gate": south_gate,
         "mayor_house": mayor_house, "well": well, "stables": stable})
    db.set_location(tavern, town,
        "A smoky tavern with low oak beams, smells of stale beer and woodsmoke",
        "Crowded tonight",
        {"outside": town, "cellar": cellar})
    db.set_location(cellar, tavern,
        "Dark and damp, barrels line the walls, rats skitter in corners",
        "The lock has been forced",
        {"upstairs": tavern})
    db.set_location(gate, town,
        "A heavy oak gate flanked by stone watchtowers",
        "Closed and barred for the night",
        {"south": town, "north_road": road})
    db.set_location(south_gate, town,
        "A smaller gate facing the river road",
        "Open, a guard dozes on a stool",
        {"north": town, "south_road": south_road, "river": river})
    db.set_location(market, town,
        "Open-air market with wooden stalls, shuttered for the night",
        "A stray dog gnaws a bone under a stall",
        {"square": town, "stables": stable})
    db.set_location(temple, town,
        "A modest stone temple with a cracked bell tower",
        "Candles flickering in the windows",
        {"outside": town})
    db.set_location(mayor_house, town,
        "A large timber house with iron-barred windows, the mayor's residence",
        "Dark and locked, no one has entered in days",
        {"outside": town})
    db.set_location(well, town,
        "The town well, stone-rimmed and ancient",
        "The water has a faint greenish tinge",
        {"square": town})
    db.set_location(stable, town,
        "Wooden stables smelling of hay and horse, a few tired mules stand in stalls",
        "The stable boy is asleep in the hay",
        {"square": town, "market": market})
    # Outside town
    db.set_location(road, None,
        "A muddy road winding north through dark forest",
        "Bandit tracks visible in the mud",
        {"gate": gate, "forest": forest})
    db.set_location(south_road, None,
        "A well-worn trade road heading south along the river",
        "Cart ruts and hoof prints mark the way",
        {"gate": south_gate, "farm": farm})
    db.set_location(river, None,
        "A wide, slow-moving river, the bridge is old stone",
        "Debris caught on the pilings suggests recent flooding",
        {"bridge": south_gate})
    db.set_location(forest, None,
        "Dense ancient forest, gnarled oaks block the sky, undergrowth thick",
        "Broken branches suggest something large passed recently",
        {"road": road, "camp": bandit_camp})
    db.set_location(farm, None,
        "A burned-out farmstead, charred timbers and collapsed walls",
        "Crops trampled, livestock slaughtered and left to rot",
        {"road": south_road})
    db.set_location(bandit_camp, None,
        "A clearing in the forest with crude tents and a fire pit",
        "Crates of stolen goods stacked under oilcloth, weapon racks",
        {"forest": forest})

    # === PLAYER ===
    player = db.create_entity("player", "Kael", "day 1",
        "A wandering sellsword seeking fortune, scarred and cynical")
    db.set_physical(player, 25, 25, tavern)
    db.set_stats(player, 4, 3, 5,
        {"fighting": 2, "persuasion": 2, "stealth": 1,
         "perception": 1, "survival": 1})

    # === ITEMS ===
    sword = db.create_entity("item", "Iron Sword", "day 1", "Worn but sharp")
    db.add_item(sword, player, equipped=1)
    pot1 = db.create_entity("item", "Healing Potion", "day 1", "Restores 10 HP")
    db.add_item(pot1, player, qty=2)
    lockpick = db.create_entity("item", "Lockpick Set", "day 1", "Thin steel picks")
    db.add_item(lockpick, player)
    silver_locket = db.create_entity("item", "Silver Locket", "day 1", "Contains a faded portrait, stolen from the tavern")
    voss_sword = db.create_entity("item", "Captain's Sword", "day 1", "Well-crafted steel with a griffin etching")
    bandit_axe = db.create_entity("item", "Bandit's Axe", "day 1", "Crude but heavy, stained with rust")

    # === NPCs ===
    # Old Magda - barkeeper (Active)
    magda = db.create_entity("npc", "Old Magda", "day 1",
        "Grizzled barkeeper, missing her left eye, trusts no one but pays for info")
    db.set_physical(magda, 12, 12, tavern)
    db.set_stats(magda, 2, 4, 3, {"perception": 3, "intimidation": 2, "knowledge": 2})
    db.set_relationship(magda, player, "disposition", 10, "Likes paying customers")
    db.add_goal(magda, "Find who stole her silver locket", 8)
    db.add_goal(magda, "Keep tavern running during festival", 5)

    # Garrett the Lean - thief (Active)
    garrett = db.create_entity("npc", "Garrett the Lean", "day 1",
        "Wiry pickpocket with a nervous laugh, always watching exits")
    db.set_physical(garrett, 10, 10, tavern)
    db.set_stats(garrett, 3, 3, 2,
        {"stealth": 3, "lockpicking": 2, "lying": 2, "dodge": 2})
    db.set_relationship(garrett, player, "disposition", -5, "Wary of armed strangers")
    db.set_relationship(garrett, magda, "disposition", -20, "Stole from her, terrified")
    db.add_goal(garrett, "Sell the silver locket to a fence", 9)
    db.add_goal(garrett, "Leave town before anyone finds out", 7, deadline="day 3")

    # Brother Aldric - priest (Active)
    aldric = db.create_entity("npc", "Brother Aldric", "day 1",
        "Elderly priest, kind but hiding a terrible secret")
    db.set_physical(aldric, 8, 8, temple)
    db.set_stats(aldric, 1, 5, 5,
        {"knowledge": 3, "medicine": 2, "persuasion": 2, "empathy": 3})
    db.set_relationship(aldric, player, "disposition", 15, "Welcomes all travelers")
    db.add_goal(aldric, "Protect the mayor's secret at all costs", 10)
    db.add_goal(aldric, "Heal the sick before the festival", 6)

    # Captain Voss - gate guard (Reactive)
    voss = db.create_entity("npc", "Captain Voss", "day 1",
        "Stocky guard captain, by-the-book, hates disorder")
    db.set_physical(voss, 20, 20, gate)
    db.set_stats(voss, 5, 3, 2,
        {"fighting": 3, "intimidation": 3, "perception": 2})
    db.set_relationship(voss, player, "disposition", 0, "Neutral")
    db.add_item(voss_sword, voss, equipped=1)

    # NEW: Bandit Chief Rork (Active, at bandit camp)
    rork = db.create_entity("npc", "Rork the Red", "day 1",
        "Scarred bandit chief, missing two fingers, cruel and cunning")
    db.set_physical(rork, 22, 22, bandit_camp)
    db.set_stats(rork, 5, 2, 3,
        {"fighting": 3, "intimidation": 3, "survival": 2})
    db.set_relationship(rork, player, "disposition", -30, "Hates outsiders")
    db.add_goal(rork, "Raid Millhaven during the festival", 9)
    db.add_goal(rork, "Keep weapon shipments from mayor hidden", 8)
    db.add_item(bandit_axe, rork, equipped=1)

    # NEW: Farmer Edda (Active, at farm)
    edda = db.create_entity("npc", "Farmer Edda", "day 1",
        "Weathered farmwoman, lost everything in the bandit raid, furious and desperate")
    db.set_physical(edda, 10, 10, farm)
    db.set_stats(edda, 3, 3, 2,
        {"survival": 3, "perception": 2, "fighting": 1})
    db.set_relationship(edda, player, "disposition", 5, "Desperate for help")
    db.add_goal(edda, "Get revenge on the bandits", 9)
    db.add_goal(edda, "Find shelter before winter", 7)

    # NEW: Merchant Salo (Reactive, at market)
    salo = db.create_entity("npc", "Merchant Salo", "day 1",
        "Rotund traveling merchant with a booming laugh, sells anything for the right price")
    db.set_physical(salo, 14, 14, market)
    db.set_stats(salo, 2, 4, 4,
        {"persuasion": 3, "lying": 2, "knowledge": 2, "perception": 1})
    db.set_relationship(salo, player, "disposition", 0, "A customer is a customer")

    # === WORLD FACTS ===
    # Public facts
    f_festival = db.add_fact("event",
        "The harvest festival begins in three days", "day 1", public=True)
    f_bandits = db.add_fact("event",
        "Bandits have been raiding farms north of town", "day 1", public=True)
    f_mayor = db.add_fact("event",
        "Mayor Harlan hasn't been seen in three days", "day 1", public=True)
    f_well = db.add_fact("event",
        "People have been getting sick from the town well", "day 1", public=True)
    # Teach public facts to all NPCs and player
    for eid in [player, magda, garrett, aldric, voss, edda, salo]:
        for fid in [f_festival, f_bandits, f_mayor, f_well]:
            db.teach_fact(eid, fid, "day 1", "common_knowledge")
    # Rork knows public facts too but not the well sickness
    for fid in [f_festival, f_bandits, f_mayor]:
        db.teach_fact(rork, fid, "day 1", "common_knowledge")

    # Secret facts
    f_smuggling = db.add_fact("secret",
        "Mayor Harlan has been smuggling weapons to the bandits", "day 1")
    db.teach_fact(magda, f_smuggling, "day 1", "overheard at the bar")
    db.teach_fact(aldric, f_smuggling, "day 1", "confessed by mayor")
    db.teach_fact(rork, f_smuggling, "day 1", "business partner")

    f_locket = db.add_fact("secret",
        "Garrett stole the silver locket from behind the bar", "day 1")
    db.teach_fact(garrett, f_locket, "day 1", "did it himself")

    f_tunnel = db.add_fact("secret",
        "A hidden tunnel under the temple leads outside the town walls", "day 1")
    db.teach_fact(aldric, f_tunnel, "day 1", "discovered years ago")

    f_poison = db.add_fact("secret",
        "Someone has been poisoning the town well, causing sickness", "day 1")
    db.teach_fact(aldric, f_poison, "day 1", "suspects but cannot prove")

    f_raid_plan = db.add_fact("secret",
        "Rork plans to attack Millhaven during the harvest festival", "day 1")
    db.teach_fact(rork, f_raid_plan, "day 1", "his own plan")

    f_mayor_location = db.add_fact("secret",
        "Mayor Harlan is hiding in the cellar of his own house", "day 1")
    db.teach_fact(aldric, f_mayor_location, "day 1", "mayor told him")

    # === WORLD CLOCK ===
    db.init_clock("day 1, evening", "autumn", "light rain")

    # === INITIAL EVENT LOG ===
    db.log_event("day 1, evening", "action", player,
        "Kael arrived in Millhaven as dusk fell, seeking shelter",
        {"entered": "Millhaven"})
    db.log_event("day 1, evening", "action", player,
        "Kael entered The Rusty Flagon and ordered an ale",
        {"moved_to": tavern})

    n_locs = 15
    n_npcs = 7
    n_facts = 10
    print(f"World seeded: {db_path}")
    print(f"  Locations: {n_locs}")
    print(f"  NPCs: {n_npcs} (5 active, 2 reactive)")
    print(f"  Items: 6")
    print(f"  World facts: {n_facts} (4 public, 6 secret)")
    print(f"  Player starts at: The Rusty Flagon")

    return {
        "db": db, "player": player,
        "locations": {"town": town, "tavern": tavern, "gate": gate,
                      "market": market, "temple": temple,
                      "cellar": cellar, "road": road,
                      "mayor_house": mayor_house, "river": river,
                      "south_gate": south_gate, "farm": farm,
                      "south_road": south_road, "forest": forest,
                      "bandit_camp": bandit_camp, "well": well,
                      "stable": stable},
        "npcs": {"magda": magda, "garrett": garrett,
                 "aldric": aldric, "voss": voss,
                 "rork": rork, "edda": edda, "salo": salo},
        "items": {"sword": sword, "pot1": pot1, "lockpick": lockpick,
                  "silver_locket": silver_locket,
                  "voss_sword": voss_sword, "bandit_axe": bandit_axe},
    }

if __name__ == "__main__":
    w = seed()
    from scene_assembler import SceneAssembler
    sa = SceneAssembler(w["db"])
    print("\n" + sa.assemble(w["player"]))
    w["db"].close()
