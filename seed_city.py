"""seed_city.py - Modern-day In Nomine scenario.
Harbor City: Angels vs Demons in a contemporary urban setting.
Activates all supernatural systems built in Phases 2-7."""
import os
from database import WorldDB

def seed(db_path="city.db"):
    if os.path.exists(db_path):
        os.remove(db_path)
    db = WorldDB(db_path)

    # === LOCATIONS ===
    # Hub
    downtown = db.create_entity("location", "Downtown", "night 1", "Heart of Harbor City, neon-lit streets")
    waterfront = db.create_entity("location", "Waterfront", "night 1", "Docks and warehouses along the bay")
    midtown = db.create_entity("location", "Midtown", "night 1", "Residential and commercial district")
    eastside = db.create_entity("location", "Eastside", "night 1", "Old neighborhood, churches and clinics")

    # Downtown locations
    hospital = db.create_entity("location", "St. Michael's Hospital", "night 1", "Major hospital, angel stronghold")
    golden_hour = db.create_entity("location", "The Golden Hour", "night 1", "Upscale cocktail bar")
    police_stn = db.create_entity("location", "Harbor City PD", "night 1", "Police precinct, detectives work late")

    # Waterfront locations
    rusty_anchor = db.create_entity("location", "The Rusty Anchor", "night 1", "Dive bar, demon haunt")
    warehouse = db.create_entity("location", "Pier 13 Warehouse", "night 1", "Abandoned warehouse, smuggling front")
    marina = db.create_entity("location", "Marina", "night 1", "Boats and quiet water")

    # Midtown locations
    nightclub = db.create_entity("location", "Apex Nightclub", "night 1", "Demon stronghold, pounding bass")
    apartment = db.create_entity("location", "Midtown Apartments", "night 1", "Player's apartment building")
    cafe = db.create_entity("location", "Cafe Lumiere", "night 1", "Quiet corner cafe, neutral meeting spot")
    library = db.create_entity("location", "Public Library", "night 1", "Old stone building, The Watcher's domain")

    # Eastside locations
    church = db.create_entity("location", "Holy Cross Church", "night 1", "Consecrated ground")
    clinic = db.create_entity("location", "Eastside Clinic", "night 1", "Free clinic for the underserved")
    park = db.create_entity("location", "Harbor Park", "night 1", "Dark trees and winding paths")
    factory = db.create_entity("location", "Abandoned Factory", "night 1", "Burned shell, arson suspected")

    # === CONNECTIONS ===
    # District hubs connect to each other
    db.set_location(downtown, None, "Heart of Harbor City", "night, neon lights, traffic", 
        {"waterfront": waterfront, "midtown": midtown, "eastside": eastside,
         "hospital": hospital, "golden_hour": golden_hour, "police": police_stn})
    db.set_location(waterfront, None, "Docks and warehouses", "foggy, smell of salt",
        {"downtown": downtown, "anchor": rusty_anchor, "warehouse": warehouse, "marina": marina})
    db.set_location(midtown, None, "Residential district", "apartment lights, quiet streets",
        {"downtown": downtown, "eastside": eastside, "nightclub": nightclub,
         "apartment": apartment, "cafe": cafe, "library": library})
    db.set_location(eastside, None, "Old neighborhood", "dim streetlights, quiet",
        {"downtown": downtown, "midtown": midtown,
         "church": church, "clinic": clinic, "park": park, "factory": factory})

    # Individual locations connect back to their district
    db.set_location(hospital, downtown, "Major hospital", "fluorescent lights, antiseptic smell",
        {"outside": downtown})
    db.set_location(golden_hour, downtown, "Upscale bar", "low lighting, jazz", {"outside": downtown})
    db.set_location(police_stn, downtown, "Police precinct", "buzzing phones, coffee", {"outside": downtown})
    db.set_location(rusty_anchor, waterfront, "Dive bar", "dim, sticky floor", {"outside": waterfront})
    db.set_location(warehouse, waterfront, "Warehouse", "dark, echoing, strange symbols", {"outside": waterfront})
    db.set_location(marina, waterfront, "Marina", "boats creaking, water lapping", {"outside": waterfront})
    db.set_location(nightclub, midtown, "Nightclub", "pounding bass, strobe lights", {"outside": midtown})
    db.set_location(apartment, midtown, "Apartment building", "quiet hallways, your door", {"outside": midtown})
    db.set_location(cafe, midtown, "Corner cafe", "warm, coffee smell, soft music", {"outside": midtown})
    db.set_location(library, midtown, "Old library", "hushed, towering shelves", {"outside": midtown})
    db.set_location(church, eastside, "Church", "candlelight, stained glass", {"outside": eastside})
    db.set_location(clinic, eastside, "Free clinic", "crowded waiting room", {"outside": eastside})
    db.set_location(park, eastside, "City park", "dark paths, rustling leaves", {"outside": eastside})
    db.set_location(factory, eastside, "Burned factory", "charred walls, broken glass", {"outside": eastside})

    # === ITEMS ===
    pistol = db.create_entity("item", "Concealed Pistol", "night 1", "Compact 9mm, fits under a jacket")
    body_armor = db.create_entity("item", "Body Armor", "night 1", "Concealed kevlar vest")
    phone = db.create_entity("item", "Phone", "night 1", "Smartphone")
    keys = db.create_entity("item", "Apartment Keys", "night 1", "Keys to your Midtown apartment")
    voss_gun = db.create_entity("item", "Service Pistol", "night 1", "Standard police sidearm")
    demon_knife = db.create_entity("item", "Obsidian Knife", "night 1", "Wickedly sharp, feels wrong")

    # === PLAYER CHARACTER ===
    player = db.create_entity("player", "Kael", "night 1",
        "A Malakite of War in human vessel. Sent to investigate demonic activity at the Waterfront.")
    db.set_physical(player, 30, 30, apartment)
    db.set_stats(player, 5, 5, 3, 3, 6, 5,
        {"fighting": 3, "perception": 2, "survival": 1, "intimidation": 2}, morale=10)
    db.set_supernatural(player, "angel", 3, 2, 4, 9, 9, 0, "malakite", "michael")
    db.add_song(player, "shields", "corporeal", 2)
    db.add_song(player, "thunder", "corporeal", 2)
    db.add_song(player, "thunder", "celestial", 1)
    db.add_attunement(player, "Malakite of War", "michael", "Sense honor and dishonor in those you meet", 1)
    db.add_vessel(player, "Kael Morrison", level=3, hp=30, hp_max=30)
    db.add_role(player, "Security Consultant", level=2, desc="Freelance security work, covers odd hours")
    db.add_item(pistol, player, equipped=1)
    db.set_item_stats(pistol, "weapon", weapon_base=5, weapon_type="piercing", weight=1.0, value=400)
    db.add_item(body_armor, player, equipped=1)
    db.set_item_stats(body_armor, "armor", armor_value=3, weight=3.0, value=500)
    db.add_item(phone, player)
    db.set_item_stats(phone, "misc", weight=0.2, value=800)
    db.add_item(keys, player)
    db.set_item_stats(keys, "misc", weight=0.1)
    db.set_currency(player, 200)
    db.set_survival(player, 0, 0, 0)

    # === ANGEL NPCs ===
    # Dr. Sarah Chen - Vessel of Raphael, Mercurian of Trade
    chen = db.create_entity("npc", "Dr. Sarah Chen", "night 1",
        "Surgeon at St. Michael's. Warm but guarded. Healer.")
    db.set_physical(chen, 20, 20, hospital)
    db.set_stats(chen, 2, 3, 5, 5, 4, 5, {"medicine": 3, "perception": 2, "knowledge": 2}, morale=70)
    db.set_supernatural(chen, "angel", 2, 3, 3, 8, 8, 0, "mercurian", "marc")
    db.add_song(chen, "healing", "corporeal", 3)
    db.add_song(chen, "healing", "ethereal", 2)
    db.add_song(chen, "healing", "celestial", 1)
    db.add_attunement(chen, "Mercurian of Trade", "marc", "Sense the value of any transaction", 1)
    db.add_vessel(chen, "Dr. Sarah Chen", level=4, hp=20, hp_max=20)
    db.add_role(chen, "Surgeon", level=4, desc="Chief surgeon, ER")
    db.set_relationship(chen, player, "disposition", 5, "Fellow angel, cautious trust")
    db.add_goal(chen, "Protect the hospital from demonic influence", 8)
    db.add_goal(chen, "Heal without drawing Disturbance", 6)

    # Officer Ward - Vessel of Uriel, Elohite of Judgment
    ward = db.create_entity("npc", "Officer James Ward", "night 1",
        "Detective investigating unusual deaths. Calm, methodical.")
    db.set_physical(ward, 22, 22, police_stn)
    db.set_stats(ward, 4, 4, 4, 4, 5, 5, {"fighting": 2, "perception": 3, "investigation": 3}, morale=25)
    db.set_supernatural(ward, "angel", 3, 2, 3, 8, 8, 0, "elohite", "dominic")
    db.add_song(ward, "thunder", "corporeal", 2)
    db.add_song(ward, "tongues", "ethereal", 2)
    db.add_attunement(ward, "Elohite of Judgment", "dominic", "Detect falsehood objectively", 1)
    db.add_vessel(ward, "James Ward", level=3, hp=22, hp_max=22)
    db.add_role(ward, "Police Detective", level=3, desc="Homicide, 10 years on the force")
    db.add_item(voss_gun, ward, equipped=1)
    db.set_item_stats(voss_gun, "weapon", weapon_base=5, weapon_type="piercing", weight=1.2, value=500)
    db.set_relationship(ward, player, "disposition", 0, "Unknown, assessing")
    db.add_goal(ward, "Investigate deaths near the Waterfront", 9)
    db.add_goal(ward, "Keep partner Rosa safe from the truth", 7)

    # === DEMON NPCs ===
    # Marco Vesari - Vessel of Azazel, Impudite of Lust
    marco = db.create_entity("npc", "Marco Vesari", "night 1",
        "Nightclub owner. Charming, dangerous. Controls the Waterfront.")
    db.set_physical(marco, 25, 25, nightclub)
    db.set_stats(marco, 5, 4, 4, 3, 5, 4, {"fighting": 3, "persuasion": 3, "intimidation": 2}, morale=20)
    db.set_supernatural(marco, "demon", 3, 2, 3, 8, 8, 0, "impudite", "andrealphus")
    db.add_song(marco, "tongues", "ethereal", 3)
    db.add_song(marco, "motion", "corporeal", 2)
    db.add_attunement(marco, "Impudite of Lust", "andrealphus", "Drain Essence through touch", 0)
    db.add_vessel(marco, "Marco Vesari", level=4, hp=25, hp_max=25)
    db.add_role(marco, "Club Owner", level=4, desc="Owner of Apex Nightclub, connected")
    db.set_relationship(marco, player, "disposition", -10, "Senses an angelic presence")
    db.add_goal(marco, "Complete the Tether to Hell at Pier 13", 10)
    db.add_goal(marco, "Expand influence through Apex Nightclub", 7)

    # Nina Voss - Free Lilim, tattoo artist, information broker
    nina = db.create_entity("npc", "Nina Voss", "night 1",
        "Tattoo artist. Plays both sides. Knows everything for a price.")
    db.set_physical(nina, 16, 16, rusty_anchor)
    db.set_stats(nina, 2, 4, 5, 4, 4, 5, {"persuasion": 3, "lying": 3, "perception": 2, "stealth": 2}, morale=60)
    db.set_supernatural(nina, "demon", 2, 3, 2, 7, 7, 0, "lilim", None)
    db.add_song(nina, "tongues", "ethereal", 2)
    db.add_song(nina, "tongues", "celestial", 1)
    db.add_attunement(nina, "Lilim Resonance", None, "Sense what someone needs or desires", 1)
    db.add_vessel(nina, "Nina Voss", level=2, hp=16, hp_max=16)
    db.add_role(nina, "Tattoo Artist", level=2, desc="Runs Needle & Thread on the waterfront")
    db.set_relationship(nina, player, "disposition", 0, "Potential customer")
    db.set_relationship(nina, marco, "disposition", -5, "Sells info about him")
    db.add_goal(nina, "Stay free — owe no Geas to anyone", 9)
    db.add_goal(nina, "Sell information to the highest bidder", 6)

    # The Watcher - Ancient Seraph of Destiny, runs the library
    watcher = db.create_entity("npc", "The Watcher", "night 1",
        "Old librarian. Ancient angel of Destiny. Knows everything, acts on nothing.")
    db.set_physical(watcher, 15, 15, library)
    db.set_stats(watcher, 1, 1, 6, 6, 6, 6, {"knowledge": 4, "perception": 4, "empathy": 3}, morale=90)
    db.set_supernatural(watcher, "angel", 1, 3, 5, 9, 9, 0, "seraph", "yves")
    db.add_song(watcher, "tongues", "celestial", 3)
    db.add_song(watcher, "tongues", "ethereal", 2)
    db.add_attunement(watcher, "Seraph of Destiny", "yves", "See the destined path of any being", 1)
    db.add_vessel(watcher, "Mr. Solomon", level=2, hp=15, hp_max=15)
    db.add_role(watcher, "Librarian", level=3, desc="Head librarian, 30 years at the post")
    db.set_relationship(watcher, player, "disposition", 10, "Sees potential in the young warrior")
    db.add_goal(watcher, "Observe the unfolding destiny at the Waterfront", 10)
    db.add_goal(watcher, "Guide without interfering — Yves's way", 8)

    # === HUMAN NPCs ===
    # Detective Rosa Morales - human cop
    rosa = db.create_entity("npc", "Detective Rosa Morales", "night 1",
        "Ward's partner. Sharp, suspicious. Getting too close to the truth.")
    db.set_physical(rosa, 14, 14, police_stn)
    db.set_stats(rosa, 3, 4, 4, 3, 4, 4, {"fighting": 2, "investigation": 3, "perception": 2}, morale=30)
    db.set_relationship(rosa, player, "disposition", 0, "Who are you?")
    db.set_relationship(rosa, ward, "disposition", 15, "Trusts her partner, mostly")
    db.add_goal(rosa, "Solve the Waterfront murders", 8)
    db.add_goal(rosa, "Figure out what Ward is hiding", 6)

    # Father Thomas - human priest
    thomas = db.create_entity("npc", "Father Thomas", "night 1",
        "Parish priest at Holy Cross. Devout. Senses something supernatural.")
    db.set_physical(thomas, 10, 10, church)
    db.set_stats(thomas, 2, 2, 4, 3, 5, 4, {"knowledge": 3, "empathy": 3, "persuasion": 2}, morale=80)
    db.set_relationship(thomas, player, "disposition", 5, "Welcomes all seekers")
    db.add_goal(thomas, "Understand the strange symbol in the church basement", 7)
    db.add_goal(thomas, "Protect his flock from the violence spreading", 8)

    # Danny Park - human bartender
    danny = db.create_entity("npc", "Danny Park", "night 1",
        "Bartender at The Rusty Anchor. Hears everything. Trustworthy for cash.")
    db.set_physical(danny, 12, 12, rusty_anchor)
    db.set_stats(danny, 3, 3, 3, 3, 3, 4, {"perception": 2, "persuasion": 2, "knowledge": 1}, morale=50)
    db.set_relationship(danny, player, "disposition", 0, "New face")
    db.set_currency(danny, 50)
    db.add_goal(danny, "Keep The Rusty Anchor running and stay out of trouble", 6)

    # Mira Okafor - human nurse
    mira = db.create_entity("npc", "Mira Okafor", "night 1",
        "Nurse at the Eastside Clinic. Compassionate. Potential target in the War.")
    db.set_physical(mira, 10, 10, clinic)
    db.set_stats(mira, 2, 3, 4, 3, 4, 3, {"medicine": 3, "empathy": 2, "perception": 1}, morale=70)
    db.set_relationship(mira, player, "disposition", 0, "Unknown")
    db.add_goal(mira, "Help the patients at the clinic", 7)
    db.add_goal(mira, "Find out why people keep disappearing near Pier 13", 5)

    # === KNOWLEDGE & FACTS ===
    # Teach all entities about each other
    for eid in [player, chen, ward, marco, nina, watcher, rosa, thomas, danny, mira]:
        db.teach_fact(eid, db.add_fact("npc", f"Knows own identity and role", "night 1", False), "night 1")

    # Public facts
    f_violence = db.add_fact("event", "Spike in unexplained violence at the Waterfront", "night 1", True)
    f_hospital = db.add_fact("event", "St. Michael's Hospital received an anonymous large donation", "night 1", True)
    f_apex = db.add_fact("event", "Apex Nightclub opened three months ago and is packed every night", "night 1", True)
    f_fire = db.add_fact("event", "The old Eastside factory burned last month — arson suspected", "night 1", True)
    f_missing = db.add_fact("event", "Several homeless people have gone missing near Pier 13", "night 1", True)

    # Secret facts
    f_tether = db.add_fact("secret", "Marco Vesari is building a Tether to Hell in Pier 13 warehouse", "night 1", False)
    db.teach_fact(marco, f_tether, "night 1", "his own plan")

    f_miracle = db.add_fact("secret", "Dr. Chen healed a gunshot wound using a Song — a nurse witnessed it", "night 1", False)
    db.teach_fact(chen, f_miracle, "night 1", "she did it")

    f_rosa_close = db.add_fact("secret", "Detective Rosa is getting too close to supernatural truth", "night 1", False)
    db.teach_fact(ward, f_rosa_close, "night 1", "observing his partner")

    f_watcher_knows = db.add_fact("secret", "The Tether is forming — the Watcher senses it but observes only", "night 1", False)
    db.teach_fact(watcher, f_watcher_knows, "night 1", "perceived through Symphony")
    db.teach_fact(watcher, f_tether, "night 1", "sensed destiny unfolding")

    f_symbol = db.add_fact("secret", "Strange infernal symbol found in Holy Cross Church basement", "night 1", False)
    db.teach_fact(thomas, f_symbol, "night 1", "found it himself")

    f_nina_sells = db.add_fact("secret", "Nina sells information to both angels and demons", "night 1", False)
    db.teach_fact(nina, f_nina_sells, "night 1", "her own business")

    # Player starts knowing public facts + mission briefing
    f_mission = db.add_fact("mission", "Michael's orders: investigate demonic activity at the Waterfront", "night 1", False)
    db.teach_fact(player, f_mission, "night 1", "from Superior")
    for f in [f_violence, f_hospital, f_apex, f_fire, f_missing]:
        for eid in [player, chen, ward, marco, nina, watcher, rosa, thomas, danny, mira]:
            db.teach_fact(eid, f, "night 1", "common knowledge")

    # === CLOCK ===
    db.init_clock("night 1, 9pm", "winter", "cold and clear")

    # === COUNTS ===
    n_locs = 17
    n_npcs = 9
    n_items = 6
    print(f"City seeded: {db_path}")
    print(f"  Locations: {n_locs}")
    print(f"  NPCs: {n_npcs} (3 angels, 2 demons, 4 humans)")
    print(f"  Items: {n_items}")
    print(f"  World facts: {5} public, {5} secret")
    print(f"  Player starts at: Midtown Apartments")

    return {
        "db": db, "player": player,
        "locations": {
            "downtown": downtown, "waterfront": waterfront,
            "midtown": midtown, "eastside": eastside,
            "hospital": hospital, "golden_hour": golden_hour,
            "police": police_stn, "anchor": rusty_anchor,
            "warehouse": warehouse, "marina": marina,
            "nightclub": nightclub, "apartment": apartment,
            "cafe": cafe, "library": library,
            "church": church, "clinic": clinic,
            "park": park, "factory": factory,
        },
        "npcs": {
            "chen": chen, "ward": ward, "marco": marco,
            "nina": nina, "watcher": watcher,
            "rosa": rosa, "thomas": thomas,
            "danny": danny, "mira": mira,
        },
        "items": {
            "pistol": pistol, "body_armor": body_armor,
            "phone": phone, "keys": keys,
            "voss_gun": voss_gun, "demon_knife": demon_knife,
        },
    }

if __name__ == "__main__":
    seed()
