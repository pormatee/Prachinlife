from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


# ============================================================
# PRACHINLIFE
# Vegetarian Collector V2 Clean
# ============================================================


# ============================================================
# CONFIG
# ============================================================

OUTPUT_FILE = Path("vegetarian_index.json")

REQUEST_TIMEOUT = 45

MAX_RETRIES = 2

SLEEP_BETWEEN_REQUESTS = 1.0


OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


# ============================================================
# THAILAND PROVINCES
# ============================================================

PROVINCES = [
    "กรุงเทพมหานคร",
    "กระบี่",
    "กาญจนบุรี",
    "กาฬสินธุ์",
    "กำแพงเพชร",
    "ขอนแก่น",
    "จันทบุรี",
    "ฉะเชิงเทรา",
    "ชลบุรี",
    "ชัยนาท",
    "ชัยภูมิ",
    "ชุมพร",
    "เชียงราย",
    "เชียงใหม่",
    "ตรัง",
    "ตราด",
    "ตาก",
    "นครนายก",
    "นครปฐม",
    "นครพนม",
    "นครราชสีมา",
    "นครศรีธรรมราช",
    "นครสวรรค์",
    "นนทบุรี",
    "นราธิวาส",
    "น่าน",
    "บึงกาฬ",
    "บุรีรัมย์",
    "ปทุมธานี",
    "ประจวบคีรีขันธ์",
    "ปราจีนบุรี",
    "ปัตตานี",
    "พระนครศรีอยุธยา",
    "พะเยา",
    "พังงา",
    "พัทลุง",
    "พิจิตร",
    "พิษณุโลก",
    "เพชรบุรี",
    "เพชรบูรณ์",
    "แพร่",
    "ภูเก็ต",
    "มหาสารคาม",
    "มุกดาหาร",
    "แม่ฮ่องสอน",
    "ยโสธร",
    "ยะลา",
    "ร้อยเอ็ด",
    "ระนอง",
    "ระยอง",
    "ราชบุรี",
    "ลพบุรี",
    "ลำปาง",
    "ลำพูน",
    "เลย",
    "ศรีสะเกษ",
    "สกลนคร",
    "สงขลา",
    "สตูล",
    "สมุทรปราการ",
    "สมุทรสงคราม",
    "สมุทรสาคร",
    "สระแก้ว",
    "สระบุรี",
    "สิงห์บุรี",
    "สุโขทัย",
    "สุพรรณบุรี",
    "สุราษฎร์ธานี",
    "สุรินทร์",
    "สุราษฎร์ธานี",
    "หนองคาย",
    "หนองบัวลำภู",
    "อ่างทอง",
    "อำนาจเจริญ",
    "อุดรธานี",
    "อุตรดิตถ์",
    "อุทัยธานี",
    "อุบลราชธานี",
]


# ลบจังหวัดซ้ำโดยรักษาลำดับเดิม
PROVINCES = list(
    dict.fromkeys(
        PROVINCES
    )
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def get_coordinates(element):
    if element.get("type") == "node":

        latitude = element.get("lat")
        longitude = element.get("lon")

    else:

        center = element.get("center") or {}

        latitude = center.get("lat")
        longitude = center.get("lon")

    if latitude is None or longitude is None:
        return None, None

    try:
        return (
            float(latitude),
            float(longitude),
        )

    except (TypeError, ValueError):
        return None, None


# ============================================================
# FOOD TYPE
# ============================================================

def get_food_types(tags):
    food_types = []

    vegetarian_value = clean_text(
        tags.get("diet:vegetarian")
    )

    vegan_value = clean_text(
        tags.get("diet:vegan")
    )

    # สำคัญ:
    # ใช้เฉพาะ ONLY
    # ไม่ใช้ YES เพราะอาจเป็นร้านทั่วไป
    # ที่มีเพียงบางเมนู
    if vegetarian_value == "only":
        food_types.append(
            "vegetarian"
        )

    if vegan_value == "only":
        food_types.append(
            "vegan"
        )

    return food_types


# ============================================================
# CATEGORY
# ============================================================

def get_category(tags):
    amenity = clean_text(
        tags.get("amenity")
    )

    allowed = {
        "restaurant",
        "cafe",
        "fast_food",
    }

    if amenity in allowed:
        return amenity

    return "restaurant"


def get_category_label(tags):
    mapping = {
        "restaurant": "ร้านอาหาร",
        "cafe": "คาเฟ่",
        "fast_food": "อาหารจานด่วน",
    }

    return mapping.get(
        tags.get("amenity"),
        "ร้านอาหาร",
    )


# ============================================================
# SOURCE
# ============================================================

def build_source_url(
    element_type,
    osm_id,
):
    if (
        not element_type
        or osm_id is None
    ):
        return None

    return (
        "https://www.openstreetmap.org/"
        f"{element_type}/{osm_id}"
    )


# ============================================================
# LOCATION
# ============================================================

def build_location(
    tags,
    latitude,
    longitude,
    province,
):
    return {
        "subdistrict": (
            clean_text(
                tags.get(
                    "addr:subdistrict"
                )
            )
            or
            clean_text(
                tags.get(
                    "addr:suburb"
                )
            )
        ),

        "district": (
            clean_text(
                tags.get(
                    "addr:district"
                )
            )
            or
            clean_text(
                tags.get(
                    "addr:city"
                )
            )
        ),

        "province": (
            clean_text(
                tags.get(
                    "addr:province"
                )
            )
            or
            clean_text(
                tags.get(
                    "addr:state"
                )
            )
            or
            province
        ),

        "country": "TH",

        "latitude": latitude,

        "longitude": longitude,
    }


# ============================================================
# QUERY
# ============================================================

def build_query(province):
    return f"""
[out:json][timeout:30];

area
  ["boundary"="administrative"]
  ["admin_level"="4"]
  ["name:th"="{province}"]
  ->.province;

(
  nwr
    ["amenity"~"restaurant|cafe|fast_food"]
    ["diet:vegetarian"="only"]
    (area.province);

  nwr
    ["amenity"~"restaurant|cafe|fast_food"]
    ["diet:vegan"="only"]
    (area.province);
);

out center tags;
"""


# ============================================================
# FETCH ONE PROVINCE
# ============================================================

def fetch_province(province):
    query = build_query(
        province
    )

    print()
    print(
        f"[FETCH] {province}"
    )

    last_error = None

    for endpoint in OVERPASS_ENDPOINTS:

        for attempt in range(
            1,
            MAX_RETRIES + 1,
        ):

            try:

                print(
                    f"  endpoint = {endpoint}"
                )

                print(
                    f"  attempt  = {attempt}"
                )

                response = requests.post(
                    endpoint,
                    data={
                        "data": query,
                    },
                    headers={
                        "User-Agent":
                            "PrachinLife-VegetarianCollector/2.0"
                    },
                    timeout=REQUEST_TIMEOUT,
                )

                response.raise_for_status()

                data = response.json()

                elements = data.get(
                    "elements",
                    [],
                )

                print(
                    f"  received = {len(elements)}"
                )

                return (
                    elements,
                    True,
                )

            except (
                requests.RequestException,
                ValueError,
            ) as error:

                last_error = error

                print(
                    "  failed =",
                    str(error),
                )

                time.sleep(2)


    print(
        f"[SKIP] {province}"
    )

    if last_error:

        print(
            "  last error =",
            str(last_error),
        )

    return (
        [],
        False,
    )


# ============================================================
# NORMALIZE
# ============================================================

def normalize_element(
    element,
    province,
):
    tags = (
        element.get("tags")
        or {}
    )

    title = (
        clean_text(
            tags.get("name:th")
        )
        or
        clean_text(
            tags.get("name")
        )
        or
        clean_text(
            tags.get("brand")
        )
    )

    # ไม่มีชื่อ ไม่เอา
    if not title:
        return None


    food_types = get_food_types(
        tags
    )

    # ต้องเป็น only จริง
    if not food_types:
        return None


    latitude, longitude = (
        get_coordinates(
            element
        )
    )


    element_type = (
        element.get("type")
    )

    osm_id = (
        element.get("id")
    )


    source_url = (
        build_source_url(
            element_type,
            osm_id,
        )
    )


    opening_hours = (
        clean_text(
            tags.get(
                "opening_hours"
            )
        )
    )


    phone = (
        clean_text(
            tags.get(
                "contact:phone"
            )
        )
        or
        clean_text(
            tags.get(
                "phone"
            )
        )
    )


    website = (
        clean_text(
            tags.get(
                "contact:website"
            )
        )
        or
        clean_text(
            tags.get(
                "website"
            )
        )
    )


    cuisine_raw = (
        clean_text(
            tags.get(
                "cuisine"
            )
        )
    )

    cuisine = []

    if cuisine_raw:

        cuisine = [
            item.strip()
            for item
            in cuisine_raw.split(";")
            if item.strip()
        ]


    return {
        "id":
            f"osm-{element_type}-{osm_id}",

        "title":
            title,

        "content_type":
            "vegetarian",

        "category":
            get_category(
                tags
            ),

        "food_types":
            food_types,

        "location":
            build_location(
                tags,
                latitude,
                longitude,
                province,
            ),

        "metadata": {
            "category_label":
                get_category_label(
                    tags
                ),

            "opening_hours":
                opening_hours,

            "phone":
                phone,

            "website":
                website,

            "cuisine":
                cuisine,

            "diet_vegetarian":
                clean_text(
                    tags.get(
                        "diet:vegetarian"
                    )
                ),

            "diet_vegan":
                clean_text(
                    tags.get(
                        "diet:vegan"
                    )
                ),

            "source_name":
                "OpenStreetMap",

            "source_url":
                source_url,

            "verified":
                True,
        },

        "source":
            "OpenStreetMap",

        "source_url":
            source_url,

        "collected_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }


# ============================================================
# BUILD RECORDS
# ============================================================

def build_records(
    province,
    elements,
):
    records = []

    for element in elements:

        record = normalize_element(
            element,
            province,
        )

        if record:

            records.append(
                record
            )

    return records


# ============================================================
# DEDUPLICATE
# ============================================================

def deduplicate_records(
    records,
):
    unique = {}

    for record in records:

        record_id = record.get(
            "id"
        )

        if not record_id:
            continue

        unique[
            record_id
        ] = record

    return list(
        unique.values()
    )


# ============================================================
# SORT
# ============================================================

def sort_records(records):
    return sorted(
        records,
        key=lambda item: (
            str(
                item
                .get(
                    "location",
                    {}
                )
                .get(
                    "province"
                )
                or ""
            ),

            str(
                item.get(
                    "title"
                )
                or ""
            ),
        )
    )


# ============================================================
# EXISTING FILE SAFETY
# ============================================================

def load_existing_records():
    if not OUTPUT_FILE.exists():
        return []

    try:

        with OUTPUT_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

        if isinstance(
            data,
            list,
        ):

            return data

    except Exception as error:

        print(
            "[WARN] Cannot read existing index:",
            error,
        )

    return []


# ============================================================
# WRITE
# ============================================================

def write_index(records):
    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")

    print()
    print(
        f"Saved {len(records)} places "
        f"to {OUTPUT_FILE}"
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    records,
    successful_provinces,
    failed_provinces,
):
    vegetarian_count = sum(
        "vegetarian"
        in item.get(
            "food_types",
            [],
        )

        for item
        in records
    )


    vegan_count = sum(
        "vegan"
        in item.get(
            "food_types",
            [],
        )

        for item
        in records
    )


    print()
    print("=" * 60)

    print(
        "SUMMARY"
    )

    print("-" * 60)

    print(
        "Successful provinces =",
        successful_provinces,
    )

    print(
        "Failed provinces =",
        failed_provinces,
    )

    print(
        "Total places =",
        len(records),
    )

    print(
        "Vegetarian only =",
        vegetarian_count,
    )

    print(
        "Vegan only =",
        vegan_count,
    )

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)

    print(
        "PrachinLife "
        "Vegetarian Collector V2 Clean"
    )

    print("=" * 60)

    print(
        "Policy:"
    )

    print(
        "- diet:vegetarian=only"
    )

    print(
        "- diet:vegan=only"
    )

    print(
        "- restaurant / cafe / fast_food only"
    )

    print(
        "- query province by province"
    )

    print("=" * 60)


    existing_records = (
        load_existing_records()
    )


    all_records = []

    successful_provinces = 0

    failed_provinces = 0


    for index, province in enumerate(
        PROVINCES,
        start=1,
    ):

        print()
        print(
            f"[{index}/{len(PROVINCES)}]"
        )


        elements, success = (
            fetch_province(
                province
            )
        )


        if not success:

            failed_provinces += 1

            continue


        successful_provinces += 1


        records = build_records(
            province,
            elements,
        )


        print(
            f"[FOUND] {province} "
            f"= {len(records)}"
        )


        all_records.extend(
            records
        )


        time.sleep(
            SLEEP_BETWEEN_REQUESTS
        )


    all_records = (
        deduplicate_records(
            all_records
        )
    )


    all_records = (
        sort_records(
            all_records
        )
    )


    print_summary(
        all_records,
        successful_provinces,
        failed_provinces,
    )


    # ========================================================
    # SAFETY
    #
    # ถ้า Overpass ล้มทั้งหมด
    # ห้ามเขียน [] ทับ index เดิม
    # ========================================================

    if (
        successful_provinces == 0
    ):

        print()

        print(
            "[ABORT WRITE]"
        )

        print(
            "No province was fetched successfully."
        )

        print(
            f"Existing index preserved "
            f"({len(existing_records)} records)."
        )

        return


    # ถ้าอย่างน้อยมี request สำเร็จ
    # แต่ไม่มีร้าน only จริง ๆ
    # ให้เตือนก่อน
    if (
        len(all_records) == 0
    ):

        print()

        print(
            "[WARNING]"
        )

        print(
            "No strict vegetarian / vegan "
            "places were found."
        )

        print(
            "Existing index preserved."
        )

        return


    write_index(
        all_records
    )


    print()
    print(
        "DONE"
    )


if __name__ == "__main__":
    main()
