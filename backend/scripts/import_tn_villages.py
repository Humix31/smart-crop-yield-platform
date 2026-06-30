"""
Import official Tamil Nadu village data into the frontend location JSON.

Usage:
  python backend/scripts/import_tn_villages.py official_villages.csv
  python backend/scripts/import_tn_villages.py official_villages.json --output frontend/src/data/tamilNaduLocations.json

The input must come from an official government source such as LGD/data.gov.in,
Tamil Nadu government, or Census/government village directory. This script does
not create or guess village names.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

STATE_COLUMNS = ["state_name", "state", "State Name", "STATE_NAME"]
DISTRICT_COLUMNS = ["district_name", "district", "District Name", "DISTRICT_NAME"]
TALUK_COLUMNS = ["subdistrict_name", "taluk_name", "sub_district_name", "Subdistrict Name", "Taluk Name", "SUBDISTRICT_NAME"]
VILLAGE_COLUMNS = ["village_name", "village", "Village Name", "VILLAGE_NAME"]
TN_DISTRICTS = {
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri", "Dindigul",
    "Erode", "Kallakurichi", "Kancheepuram", "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai",
    "Nagapattinam", "Kanniyakumari", "Namakkal", "Perambalur", "Pudukottai", "Ramanathapuram",
    "Ranipet", "Salem", "Sivagangai", "Tenkasi", "Thanjavur", "Theni", "Thiruvallur",
    "Thiruvarur", "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tirupathur", "Tiruppur",
    "Tiruvannamalai", "The Nilgiris", "Vellore", "Viluppuram", "Virudhunagar",
}


def pick(row: dict[str, Any], candidates: list[str]) -> str:
    for key in candidates:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("records", "data", "items", "villages"):
                if isinstance(data.get(key), list):
                    return data[key]
    raise SystemExit("Input must be a CSV or JSON array/object with official village records")


def normalize(rows: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    locations: dict[str, dict[str, set[str]]] = {}
    for row in rows:
        state = pick(row, STATE_COLUMNS)
        if state and state.lower() not in {"tamil nadu", "tamilnadu"}:
            continue
        district = pick(row, DISTRICT_COLUMNS)
        taluk = pick(row, TALUK_COLUMNS)
        village = pick(row, VILLAGE_COLUMNS)
        if not district or not taluk or not village:
            continue
        locations.setdefault(district, {}).setdefault(taluk, set()).add(village)
    return {
        district: {taluk: sorted(villages) for taluk, villages in sorted(taluks.items())}
        for district, taluks in sorted(locations.items())
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import official Tamil Nadu village data")
    parser.add_argument("input", help="Official CSV/JSON file from LGD/data.gov.in/TN govt/Census")
    parser.add_argument("--output", default="frontend/src/data/tamilNaduLocations.json")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    rows = load_rows(input_path)
    locations = normalize(rows)
    total_districts = len(locations)
    total_taluks = sum(len(taluks) for taluks in locations.values())
    total_villages = sum(len(villages) for taluks in locations.values() for villages in taluks.values())
    missing_districts = sorted(TN_DISTRICTS - set(locations.keys()))
    zero_village_taluks = [f"{district} / {taluk}" for district, taluks in locations.items() for taluk, villages in taluks.items() if not villages]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(locations, ensure_ascii=False, indent=2) + "
", encoding="utf-8")

    print(f"Total districts: {total_districts}")
    print(f"Total taluks: {total_taluks}")
    print(f"Total villages: {total_villages}")
    print(f"Missing districts: {missing_districts}")
    print(f"Taluks with zero villages: {zero_village_taluks}")
    if total_villages == 0:
        raise SystemExit("No villages imported. Check that the input contains official village_name columns for Tamil Nadu.")


if __name__ == "__main__":
    main()
