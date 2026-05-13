"""disturbance.py - Supernatural noise detection.
Every Essence spend generates Disturbance.
Songs generate additional Disturbance.
Nearby celestials can detect it."""
from dice import skill_check


class DisturbanceSystem:
    def __init__(self, db):
        self.db = db

    def get_locations_within_hops(self, start_loc_id, max_hops):
        """BFS through location connections."""
        visited = set()
        queue = [(start_loc_id, 0)]
        result = []
        while queue:
            lid, depth = queue.pop(0)
            if lid in visited:
                continue
            visited.add(lid)
            result.append((lid, depth))
            if depth < max_hops:
                loc = self.db.get_location(lid)
                if loc and loc["connections"]:
                    for key, eid in loc["connections"].items():
                        if eid not in visited:
                            queue.append((eid, depth + 1))
                # Also check reverse: locations that connect TO here
                rev = self.db.db.execute(
                    "SELECT entity_id FROM comp_location WHERE connections LIKE ?",
                    (f'%{lid}%',)).fetchall()
                for row in rev:
                    if row["entity_id"] not in visited:
                        queue.append((row["entity_id"], depth + 1))
        return result

    def check_detection(self, source_id, location_id, magnitude):
        """Check if nearby celestials detect this Disturbance.
        Hops = magnitude // 3 (mag 3=1 hop, 6=2, 9=3).
        Returns list of detection results."""
        max_hops = max(1, magnitude // 3)
        nearby_locs = self.get_locations_within_hops(location_id, max_hops)
        detections = []

        for lid, depth in nearby_locs:
            entities = self.db.get_entities_at(lid, "npc")
            for e in entities:
                if e["id"] == source_id:
                    continue
                if not self.db.is_supernatural(e["id"]):
                    continue
                stats = self.db.get_stats(e["id"])
                if not stats:
                    continue
                per = stats.get("perception", 3)
                # TN = Perception, difficulty increases with distance
                mod = magnitude - depth * 2  # high magnitude easier to detect
                roll = skill_check(per, 0, mod)
                if roll["success"]:
                    detections.append({
                        "entity_id": e["id"],
                        "entity_name": e["name"],
                        "distance": depth,
                        "detected": True,
                    })
        return detections

    def format_detections(self, detections):
        """Format for narrator."""
        if not detections:
            return "No celestials detected the Disturbance."
        parts = []
        for d in detections:
            dist_txt = "same location" if d["distance"] == 0 else f"{d['distance']} location(s) away"
            parts.append(f"{d['entity_name']} ({dist_txt})")
        return f"Detected by: {', '.join(parts)}"
