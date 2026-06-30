"""Import official Tamil Nadu LGD/revenue village data for the frontend.

Usage:
    python backend/scripts/import_tn_locations.py path/to/official_villages.csv
    python backend/scripts/import_tn_locations.py path/to/official_villages.json

Accepted flat input columns include:
    district_name, subdistrict_name or taluk_name, village_name, village_code

Output:
    frontend/src/data/tamilNaduLocations.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

TN_DISTRICTS = [
    "Ariyalur",
    "Chengalpattu",
    "Chennai",
    "Coimbatore",
    "Cuddalore",
    "Dharmapuri",
    "Dindigul",
    "Erode",
    "Kallakurichi",
    "Kancheepuram",
    "Kanniyakumari",
    "Karur",
    "Krishnagiri",
    "Madurai",
    "Mayiladuthurai",
    "Nagapattinam",
    "Namakkal",
    "Perambalur",
    "Pudukkottai",
    "Ramanathapuram",
    "Ranipet",
    "Salem",
    "Sivaganga",
    "Tenkasi",
    "Thanjavur",
    "Theni",
    "The Nilgiris",
    "Thiruvallur",
    "Thiruvarur",
    "Thoothukkudi",
    "Tiruchirappalli",
    "Tirunelveli",
    "Tirupathur",
    "Tiruppur",
    "Tiruvannamalai",
    "Vellore",
    "Viluppuram",
    "Virudhunagar",
]

DISTRICT_ALIASES = {
    "nilgiris": "The Nilgiris",
    "the nilgiris": "The Nilgiris",
    "tiruvallur": "Thiruvallur",
    "thiruvallur": "Thiruvallur",
    "tiruvarur": "Thiruvarur",
    "thiruvarur": "Thiruvarur",
    "thoothukudi": "Thoothukkudi",
    "thoothukkudi": "Thoothukkudi",
    "kanchipuram": "Kancheepuram",
    "kancheepuram": "Kancheepuram",
    "kanyakumari": "Kanniyakumari",
    "kanniyakumari": "Kanniyakumari",
    "villupuram": "Viluppuram",
    "viluppuram": "Viluppuram",
}

FIELD_ALIASES = {
    "district": ("district_name", "district", "districtname", "district name"),
    "taluk": (
        "subdistrict_name",
        "sub_district_name",
        "subdistrict",
        "sub district",
        "sub-district",
        "taluk_name",
        "taluk",
        "tehsil",
        "tehsil_name",
    ),
    "village": ("village_name", "village", "villagename", "village name"),
    "village_code": ("village_code", "villagecode", "village code", "lgd_village_code", "lgd code"),
}


def clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def key(value: str) -> str:
    return clean(value).lower().replace("_", " ").replace("-", " ")


def canonical_district(value: str) -> str:
    cleaned = clean(value)
    if not cleaned:
        return ""
    alias = DISTRICT_ALIASES.get(key(cleaned))
    if alias:
        return alias
    for district in TN_DISTRICTS:
        if key(district) == key(cleaned):
            return district
    return cleaned


def pick(row: dict[str, Any], logical_name: str) -> str:
    normalized = {key(k): v for k, v in row.items()}
    for alias in FIELD_ALIASES[logical_name]:
        if key(alias) in normalized:
            return clean(normalized[key(alias)])
    return ""


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def flatten_nested_json(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for district, taluks in data.items():
        if not isinstance(taluks, dict):
            continue
        for taluk, villages in taluks.items():
            if not isinstance(villages, list):
                continue
            for village in villages:
                if isinstance(village, dict):
                    village_name = village.get("village_name") or village.get("name") or village.get("village")
                    village_code = village.get("village_code") or village.get("code") or ""
                else:
                    village_name = village
                    village_code = ""
                rows.append(
                    {
                        "district_name": district,
                        "taluk_name": taluk,
                        "village_name": village_name,
                        "village_code": village_code,
                    }
                )
    return rows


def read_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("records"), list):
            return [row for row in data["records"] if isinstance(row, dict)]
        if isinstance(data.get("data"), list):
            return [row for row in data["data"] if isinstance(row, dict)]
        return flatten_nested_json(data)
    raise ValueError("JSON must be a list of records or a district/taluk/village object.")


def read_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv(path)
    if suffix == ".json":
        return read_json(path)
    raise ValueError("Input must be an official .csv or .json file.")


def sorted_locations(locations: dict[str, dict[str, set[str]]]) -> dict[str, dict[str, list[str]]]:
    return {
        district: {
            taluk: sorted(villages, key=str.casefold)
            for taluk, villages in sorted(taluks.items(), key=lambda item: item[0].casefold())
        }
        for district, taluks in sorted(locations.items(), key=lambda item: item[0].casefold())
    }


def import_locations(rows: Iterable[dict[str, Any]]) -> tuple[dict[str, dict[str, list[str]]], dict[str, Any]]:
    locations: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    stats = {
        "rows": 0,
        "skipped_missing_district": 0,
        "skipped_missing_taluk": 0,
        "skipped_missing_village": 0,
        "duplicates_removed": 0,
        "unknown_districts": set(),
    }

    seen: set[tuple[str, str, str]] = set()
    known = set(TN_DISTRICTS)

    for row in rows:
        stats["rows"] += 1
        district = canonical_district(pick(row, "district"))
        taluk = clean(pick(row, "taluk"))
        village = clean(pick(row, "village"))

        if not district:
            stats["skipped_missing_district"] += 1
            continue
        if not taluk:
            stats["skipped_missing_taluk"] += 1
            continue
        if not village:
            stats["skipped_missing_village"] += 1
            continue
        if district not in known:
            stats["unknown_districts"].add(district)

        dedupe_key = (district.casefold(), taluk.casefold(), village.casefold())
        if dedupe_key in seen:
            stats["duplicates_removed"] += 1
            continue
        seen.add(dedupe_key)
        locations[district][taluk].add(village)

    return sorted_locations(locations), stats


def print_summary(locations: dict[str, dict[str, list[str]]], stats: dict[str, Any]) -> None:
    districts = len(locations)
    taluks = sum(len(taluk_map) for taluk_map in locations.values())
    villages = sum(len(village_list) for taluk_map in locations.values() for village_list in taluk_map.values())

    missing_districts = [district for district in TN_DISTRICTS if district not in locations]
    missing_taluk_districts = [district for district, taluk_map in locations.items() if not taluk_map]
    missing_village_taluks = [
        f"{district} / {taluk}"
        for district, taluk_map in locations.items()
        for taluk, village_list in taluk_map.items()
        if not village_list
    ]

    print(f"Total districts: {districts}")
    print(f"Total taluks: {taluks}")
    print(f"Total villages: {villages}")
    print(f"Rows read: {stats['rows']}")
    print(f"Duplicate villages removed: {stats['duplicates_removed']}")
    print(f"Rows missing district: {stats['skipped_missing_district']}")
    print(f"Rows missing taluk: {stats['skipped_missing_taluk']}")
    print(f"Rows missing village: {stats['skipped_missing_village']}")
    print("Missing districts: " + (", ".join(missing_districts) if missing_districts else "None"))
    print("Missing taluks: " + (", ".join(missing_taluk_districts) if missing_taluk_districts else "None"))
    print("Missing villages: " + (", ".join(missing_village_taluks) if missing_village_taluks else "None"))
    unknown = sorted(stats["unknown_districts"], key=str.casefold)
    print("Unknown district names in input: " + (", ".join(unknown) if unknown else "None"))


def default_output_path() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "frontend" / "src" / "data" / "tamilNaduLocations.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import official Tamil Nadu village data into frontend JSON.")
    parser.add_argument("input", nargs="?", help="Official LGD/Tamil Nadu government village CSV or JSON file")
    parser.add_argument("--output", type=Path, default=default_output_path(), help="Output JSON path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input:
        print("Upload official LGD village CSV/JSON first.")
        return 2

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print("Upload official LGD village CSV/JSON first.")
        print(f"Missing file: {input_path}")
        return 2

    try:
        rows = read_rows(input_path)
        locations, stats = import_locations(rows)
    except Exception as exc:
        print(f"Import failed: {exc}")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(locations, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"Wrote: {args.output}")
    print_summary(locations, stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
