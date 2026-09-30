DOMAIN_PACK = {
    "domain_id": "local_life",
    "version": "1.1.0",

    "categories": {
        "vegetarian": [
            "ร้านเจ",
            "อาหารเจ",
            "กินเจ",
            "มังสวิรัติ"
        ],
        "coffee": [
            "กาแฟ",
            "คาเฟ่"
        ],
        "fuel_station": [
            "ปั๊มน้ำมัน",
            "สถานีบริการน้ำมัน",
            "ปั๊ม"
        ],
        "pharmacy": [
            "ร้านขายยา",
            "เภสัช"
        ],
        "food": [
            "อาหาร",
            "ของกิน"
        ],
    },

    "semantic_concepts": {

        "vegetarian_need": {
            "aliases": [
                "วีแกน",
                "vegan",
                "ไม่ใส่เนื้อ",
                "ผักล้วน",
                "คนไม่กินเนื้อ",
                "ไม่กินเนื้อ",
                "plant based",
                "plant-based"
            ],
            "intent": "search_place",
            "slots": {
                "category": "vegetarian"
            }
        },

        "coffee_need": {
            "aliases": [
                "คอฟฟี่",
                "coffee shop",
                "ลาเต้",
                "เอสเพรสโซ"
            ],
            "intent": "search_place",
            "slots": {
                "category": "coffee"
            }
        },

        "fuel_need": {
            "aliases": [
                "เติมน้ำมัน",
                "หาที่เติมน้ำมัน",
                "น้ำมันหมด",
                "รถหมดน้ำมัน",
                "น้ำมันใกล้หมด",
                "จะหมดน้ำมัน",
                "ไฟน้ำมันขึ้น",
                "เติมเบนซิน",
                "เติมดีเซล",
                "เติมเชื้อเพลิง",
                "ที่เติมเชื้อเพลิง",
                "น้ำมันรถเหลือน้อย",
                "แวะเติมน้ำมัน"
            ],
            "intent": "search_place",
            "slots": {
                "category": "fuel_station"
            }
        },

        "pharmacy_need": {
            "aliases": [
                "ร้านยา",
                "ซื้อยา",
                "ที่ซื้อยา",
                "ขายยา",
                "หายา"
            ],
            "intent": "search_place",
            "slots": {
                "category": "pharmacy"
            }
        },

        "food_need": {
            "aliases": [
                "หาอะไรกิน",
                "อะไรกิน",
                "ร้านข้าว",
                "กินข้าว",
                "ร้านอร่อย",
                "อยากกินข้าว"
            ],
            "intent": "search_place",
            "slots": {
                "category": "food"
            }
        },

        "promotion_need": {
            "aliases": [
                "ลดราคา",
                "ดีล"
            ],
            "intent": "search_promotion",
            "slots": {}
        }
    },

    "promotion_concepts": [
        "โปรโมชั่น",
        "โปรโมชัน",
        "ส่วนลด",
        "โปร",
        "ลดราคา",
        "ดีล"
    ],

    "search_concepts": [
        "หาร้าน",
        "ค้นหาร้าน",
        "หา",
        "มีร้าน"
    ],

    "location_modes": {
        "near_me": [
            "ใกล้ฉัน",
            "ใกล้ๆ",
            "ใกล้ ๆ",
            "แถวนี้"
        ]
    },

    "provinces": {
        "ปราจีนบุรี": [
            "จังหวัดปราจีนบุรี",
            "ปราจีนบุรี"
        ]
    },

    "districts": {
        "เมืองปราจีนบุรี": {
            "aliases": [
                "อำเภอเมืองปราจีนบุรี",
                "เมืองปราจีนบุรี"
            ],
            "province": "ปราจีนบุรี"
        },

        "กบินทร์บุรี": {
            "aliases": [
                "อำเภอกบินทร์บุรี",
                "กบินทร์บุรี",
                "กบินทร์"
            ],
            "province": "ปราจีนบุรี"
        }
    },

    "required_slots": {
        "search_place": ["category"],
        "search_promotion": []
    },

    "intent_topics": {
        "search_place": "place_search",
        "search_promotion": "promotion_search"
    }
}
