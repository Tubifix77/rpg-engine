"""economy.py - Buy/sell transactions between entities.
Checks currency, transfers items, updates balances."""


class EconomySystem:
    def __init__(self, db):
        self.db = db

    def buy_item(self, buyer_id, seller_id, item_id):
        """Buy an item from a seller. Returns result dict."""
        ist = self.db.get_item_stats(item_id)
        if not ist or ist.get("value") is None:
            return {"success": False, "reason": "Item has no price"}
        if not self.db.has_item(item_id, seller_id):
            return {"success": False, "reason": "Seller doesn't have item"}
        price = ist["value"]
        buyer_gold = self.db.get_currency(buyer_id)
        if buyer_gold < price:
            return {"success": False, "reason": f"Not enough silver ({buyer_gold}/{price})"}
        # Transfer
        self.db.update_currency(buyer_id, -price)
        self.db.update_currency(seller_id, price)
        self.db.remove_item(item_id, seller_id)
        self.db.add_item(item_id, buyer_id)
        item = self.db.get_entity(item_id)
        name = item["name"] if item else "item"
        remaining = self.db.get_currency(buyer_id)
        return {
            "success": True,
            "item": name,
            "price": price,
            "remaining": remaining,
            "summary": f"Bought {name} for {price} silver. Currency: {remaining} silver."
        }

    def sell_item(self, seller_id, buyer_id, item_id, price_modifier=0.5):
        """Sell an item. Seller gets half value by default."""
        ist = self.db.get_item_stats(item_id)
        if not ist or ist.get("value") is None:
            return {"success": False, "reason": "Item has no price"}
        if not self.db.has_item(item_id, seller_id):
            return {"success": False, "reason": "You don't have that item"}
        sell_price = max(1, int(ist["value"] * price_modifier))
        self.db.update_currency(seller_id, sell_price)
        self.db.remove_item(item_id, seller_id)
        self.db.add_item(item_id, buyer_id)
        item = self.db.get_entity(item_id)
        name = item["name"] if item else "item"
        remaining = self.db.get_currency(seller_id)
        return {
            "success": True,
            "item": name,
            "price": sell_price,
            "remaining": remaining,
            "summary": f"Sold {name} for {sell_price} silver. Currency: {remaining} silver."
        }

    def format_for_scene(self, entity_id):
        """Currency display for scene assembler."""
        gold = self.db.get_currency(entity_id)
        return f"{gold} silver" if gold > 0 else "no silver"
