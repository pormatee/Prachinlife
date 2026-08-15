from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "promotions.json"


REQUIRED_FIELDS = {
    "id",
    "promotion_type",
    "title",
    "merchant",
    "source_url",
    "source",
    "verified",
    "collected_at",
    "location_scope",
    "country",
}


ALLOWED_LOCATION_SCOPES = {
    "national",
    "province",
    "district",
    "branch",
}


def load_data() -> list[dict]:

    with DATA_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "promotions.json must contain a JSON list"
        )

    return data


def validate_required_fields(
    item: dict,
    index: int,
) -> list[str]:

    errors: list[str] = []

    missing = [
        field
        for field in REQUIRED_FIELDS
        if field not in item
    ]

    if missing:
        errors.append(
            f"record {index}: "
            f"missing fields {missing}"
        )

    for field in REQUIRED_FIELDS:

        if field not in item:
            continue

        if field in {
            "verified",
        }:
            continue

        if item.get(field) in {
            None,
            "",
        }:
            errors.append(
                f"record {index}: "
                f"{field} is empty"
            )

    if item.get("verified") is not True:
        errors.append(
            f"record {index}: "
            f"verified must be True"
        )

    return errors


def validate_identity(
    item: dict,
    index: int,
) -> list[str]:

    errors: list[str] = []

    if item.get("promotion_type") not in {
        "campaign",
        "product_deal",
        "coupon",
        "member_offer",
    }:
        errors.append(
            f"record {index}: "
            f"invalid promotion_type "
            f"{item.get('promotion_type')!r}"
        )

    return errors


def validate_location(
    item: dict,
    index: int,
) -> list[str]:

    errors: list[str] = []

    scope = item.get(
        "location_scope"
    )

    country = item.get(
        "country"
    )

    province = item.get(
        "province"
    )

    district = item.get(
        "district"
    )

    subdistrict = item.get(
        "subdistrict"
    )

    branch_name = item.get(
        "branch_name"
    )


    if (
        scope
        not in ALLOWED_LOCATION_SCOPES
    ):
        errors.append(
            f"record {index}: "
            f"invalid location_scope "
            f"{scope!r}"
        )

        return errors


    if country != "TH":

        errors.append(
            f"record {index}: "
            f"country must be 'TH'"
        )


    if scope == "national":

        local_values = {
            "province":
                province,

            "district":
                district,

            "subdistrict":
                subdistrict,

            "branch_name":
                branch_name,
        }

        populated = [
            field
            for field, value
            in local_values.items()
            if value
        ]

        if populated:

            errors.append(
                f"record {index}: "
                f"national scope must not "
                f"contain local fields "
                f"{populated}"
            )


    elif scope == "province":

        if not province:

            errors.append(
                f"record {index}: "
                f"province scope "
                f"requires province"
            )

        if district:

            errors.append(
                f"record {index}: "
                f"province scope must not "
                f"contain district"
            )

        if subdistrict:

            errors.append(
                f"record {index}: "
                f"province scope must not "
                f"contain subdistrict"
            )

        if branch_name:

            errors.append(
                f"record {index}: "
                f"province scope must not "
                f"contain branch_name"
            )


    elif scope == "district":

        if not province:

            errors.append(
                f"record {index}: "
                f"district scope "
                f"requires province"
            )

        if not district:

            errors.append(
                f"record {index}: "
                f"district scope "
                f"requires district"
            )

        if branch_name:

            errors.append(
                f"record {index}: "
                f"district scope must not "
                f"contain branch_name"
            )


    elif scope == "branch":

        if not province:

            errors.append(
                f"record {index}: "
                f"branch scope "
                f"requires province"
            )

        if not district:

            errors.append(
                f"record {index}: "
                f"branch scope "
                f"requires district"
            )

        if not branch_name:

            errors.append(
                f"record {index}: "
                f"branch scope "
                f"requires branch_name"
            )


    return errors


def validate_record(
    item: dict,
    index: int,
) -> list[str]:

    errors: list[str] = []

    errors.extend(
        validate_required_fields(
            item,
            index,
        )
    )

    errors.extend(
        validate_identity(
            item,
            index,
        )
    )

    errors.extend(
        validate_location(
            item,
            index,
        )
    )

    return errors


def main() -> None:

    print("=" * 60)
    print(
        "PrachinLife Data Validator V1.1"
    )
    print("=" * 60)

    data = load_data()

    errors: list[str] = []

    ids: set[str] = set()

    location_counts = {
        "national": 0,
        "province": 0,
        "district": 0,
        "branch": 0,
    }


    for index, item in enumerate(
        data,
        start=1,
    ):

        errors.extend(
            validate_record(
                item,
                index,
            )
        )


        item_id = item.get("id")

        if item_id:

            if item_id in ids:

                errors.append(
                    f"record {index}: "
                    f"duplicate id {item_id}"
                )

            ids.add(
                item_id
            )


        scope = item.get(
            "location_scope"
        )

        if scope in location_counts:

            location_counts[
                scope
            ] += 1


    print(
        f"Records = {len(data)}"
    )

    print(
        f"Unique IDs = {len(ids)}"
    )

    print(
        "Location counts =",
        location_counts,
    )

    print(
        f"Errors = {len(errors)}"
    )


    if errors:

        print()

        for error in errors:

            print(
                "[FAIL]",
                error,
            )

        print()

        print(
            "FINAL RESULT: FAIL"
        )

        raise SystemExit(1)


    print()

    print(
        "FINAL RESULT: PASS"
    )


if __name__ == "__main__":
    main()
