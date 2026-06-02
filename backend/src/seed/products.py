"""Christmas tree product seed data.

5 products covering different tree species. All prices in USD.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

_NOW = datetime.now(timezone.utc).isoformat()

PRODUCTS: list[dict] = [
    {
        "productId": "tree-001",
        "name": "Fraser Fir",
        "type": "Fir",
        "height": "6 ft",
        "price": Decimal("89.99"),
        "description": (
            "The Fraser Fir is the most popular Christmas tree in North America. "
            "Known for its pleasant fragrance, strong branches, and excellent needle retention."
        ),
        "careInstructions": (
            "Keep in a water-filled stand and check water level daily. "
            "Place away from heat sources. Mist branches lightly every few days."
        ),
        "imageUrl": "/trees/fraser_fir.png",
        "availabilityStatus": "IN_STOCK",
        "quantityAvailable": 25,
        "createdAt": _NOW,
        "updatedAt": _NOW,
    },
    {
        "productId": "tree-002",
        "name": "Balsam Fir",
        "type": "Fir",
        "height": "5 ft",
        "price": Decimal("69.99"),
        "description": (
            "The Balsam Fir offers a classic Christmas scent that fills any room. "
            "Soft to the touch with a traditional, full shape."
        ),
        "careInstructions": (
            "Re-cut the trunk 1 inch from the bottom before placing in water. "
            "Keep stand filled — a fresh tree can drink a quart of water per day."
        ),
        "imageUrl": "/trees/balsam_fir.png",
        "availabilityStatus": "IN_STOCK",
        "quantityAvailable": 18,
        "createdAt": _NOW,
        "updatedAt": _NOW,
    },
    {
        "productId": "tree-003",
        "name": "Douglas Fir",
        "type": "Fir",
        "height": "7 ft",
        "price": Decimal("109.99"),
        "description": (
            "A tall, stately tree with soft needles and a subtle sweet fragrance. "
            "The Douglas Fir is a classic choice for larger living rooms."
        ),
        "careInstructions": (
            "Keep indoors no longer than 4 weeks. Water daily and keep away from "
            "fireplaces, radiators, and direct sunlight."
        ),
        "imageUrl": "/trees/douglas_fir.png",
        "availabilityStatus": "IN_STOCK",
        "quantityAvailable": 12,
        "createdAt": _NOW,
        "updatedAt": _NOW,
    },
    {
        "productId": "tree-004",
        "name": "Blue Spruce",
        "type": "Spruce",
        "height": "6 ft",
        "price": Decimal("94.99"),
        "description": (
            "Striking blue-silver foliage makes the Blue Spruce a showstopper. "
            "Stiff branches hold heavy ornaments with ease."
        ),
        "careInstructions": (
            "The Blue Spruce has lower water needs than firs but still requires a "
            "full stand of water. Needles are sharp — handle with gloves."
        ),
        "imageUrl": "/trees/blue_spruce.png",
        "availabilityStatus": "IN_STOCK",
        "quantityAvailable": 10,
        "createdAt": _NOW,
        "updatedAt": _NOW,
    },
    {
        "productId": "tree-005",
        "name": "Norway Spruce",
        "type": "Spruce",
        "height": "5 ft",
        "price": Decimal("59.99"),
        "description": (
            "The traditional European Christmas tree with a classic pyramid shape. "
            "The Norway Spruce has a wonderful pine scent and a nostalgic look."
        ),
        "careInstructions": (
            "Norway Spruce drops needles faster than firs — keep well-watered and "
            "away from heat. Best displayed no more than 2–3 weeks indoors."
        ),
        "imageUrl": "/trees/norway_spruce.png",
        "availabilityStatus": "LOW_STOCK",
        "quantityAvailable": 4,
        "createdAt": _NOW,
        "updatedAt": _NOW,
    },
]
