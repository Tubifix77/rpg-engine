"""lore_config.py - Setting terminology layer.
Swap this file to switch between In Nomine (fan) and original (commercial) lore.
Engine code references LORE["key"], never hardcoded setting terms."""

# Tier 2: In Nomine fan edition
LORE = {
    # Realms
    "realm_physical": "Corporeal",
    "realm_mental": "Ethereal",
    "realm_spiritual": "Celestial",

    # Supernatural
    "supernatural_noise": "Disturbance",
    "moral_drift": "Dissonance",
    "permanent_flaw": "Discord",
    "magic_system": "Songs",
    "physical_body": "Vessel",
    "cover_identity": "Role",
    "power_level": "Forces",
    "mana": "Essence",
    "faction_ability": "Attunement",
    "faction_rank": "Distinction",

    # Factions
    "good_faction": "Heaven",
    "evil_faction": "Hell",
    "good_agents": "Angels",
    "evil_agents": "Demons",
    "good_leader": "Archangel",
    "evil_leader": "Demon Prince",
    "neutral_type": "Human",

    # Natures (alignment)
    "nature_good": "Angel",
    "nature_evil": "Demon",
    "nature_neutral": "Human",
    "nature_fallen": "Fallen",
    "nature_redeemed": "Redeemed",

    # Interventions
    "divine_miracle": "Divine Intervention",
    "infernal_miracle": "Infernal Intervention",

    # Supernatural events
    "angel_death": "Discorporation",
    "demon_death": "Discorporation",
    "soul_death": "Soul Death",
    "essence_regen": "Essence Regeneration",
}


def L(key):
    """Shorthand: L("mana") -> "Essence" """
    return LORE.get(key, key)


# Release tier info
TIER = "fan"  # "fan" = In Nomine terms, "commercial" = original terms
SETTING_NAME = "In Nomine"
SETTING_CREDIT = "In Nomine is a trademark of Steve Jackson Games."
DISCLAIMER = "This is an unofficial fan project, not affiliated with or endorsed by SJG."
