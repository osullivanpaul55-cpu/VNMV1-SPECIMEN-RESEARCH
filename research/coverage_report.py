#!/usr/bin/env python3
"""Compile public, per-taxon photo-reference coverage without granting approval."""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

SCHEMA = "VNMV1_PUBLIC_PHOTO_CANDIDATES_V1"
REPORT_SCHEMA = "VNMV1_PUBLIC_SPECIES_PHOTO_COVERAGE_V1"
MINIMUM_TARGET = 9
PREFERRED_TARGET = 12
PREFERRED_MAX_TARGET = 15
FIELDS = (
    "taxon_key", "scientific_name", "candidate_photo_records",
    "link_only_source_records", "distinct_photo_source_records",
    "minimum_target", "preferred_target", "preferred_max_target",
    "gap_to_minimum", "gap_to_preferred", "gap_to_preferred_max",
    "rights_pending_candidate_records", "visual_review_pending_candidate_records",
    "unverified_pose_hints", "unverified_behaviour_hints",
    "approved_for_imagegen_records", "review_state", "license_codes",
)

def compile_coverage(index: dict) -> dict:
    if not isinstance(index, dict) or index.get("schema") != SCHEMA:
        raise ValueError("INVALID_PUBLIC_PHOTO_INDEX")
    species = index.get("species")
    if not isinstance(species, dict):
        raise ValueError("INVALID_PUBLIC_SPECIES_MAP")
    rows = []
    for key, taxon in sorted(species.items(), key=lambda pair: (str(pair[1].get("scientific_name", "")).casefold(), pair[0])):
        if not isinstance(taxon, dict):
            raise ValueError("INVALID_PUBLIC_SPECIES_ROW")
        name = taxon.get("scientific_name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("MISSING_PUBLIC_SCIENTIFIC_NAME")
        candidates = taxon.get("candidates", [])
        leads = taxon.get("link_only_leads", [])
        if not isinstance(candidates, list) or not isinstance(leads, list):
            raise ValueError("INVALID_REFERENCE_RECORD_LIST")
        candidate_keys = set()
        link_keys = set()
        licenses = Counter()
        pose_hints = 0
        behaviour_hints = 0
        approved = 0
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError("INVALID_CANDIDATE_RECORD")
            photo_key = candidate.get("photo_key")
            if not isinstance(photo_key, str) or not photo_key:
                raise ValueError("CANDIDATE_PHOTO_KEY_REQUIRED")
            candidate_keys.add(photo_key)
            licenses[str(candidate.get("license_code") or "UNKNOWN")] += 1
            pose_hints += len(candidate.get("unverified_observer_text_pose_hints", []))
            behaviour_hints += len(candidate.get("unverified_observer_behaviour_hints", []))
            approved += candidate.get("approved_for_imagegen") is True
        for lead in leads:
            if not isinstance(lead, dict):
                raise ValueError("INVALID_LINK_ONLY_RECORD")
            photo_key = lead.get("photo_key")
            if not isinstance(photo_key, str) or not photo_key:
                raise ValueError("LINK_ONLY_PHOTO_KEY_REQUIRED")
            link_keys.add(photo_key)
            licenses[str(lead.get("license_code") or "UNKNOWN")] += 1
            pose_hints += len(lead.get("unverified_observer_text_pose_hints", []))
            behaviour_hints += len(lead.get("unverified_observer_behaviour_hints", []))
        overlap = candidate_keys & link_keys
        link_keys -= candidate_keys
        candidate_count = len(candidate_keys)
        link_count = len(link_keys)
        distinct = candidate_count + link_count
        if approved:
            raise ValueError("PUBLIC_CANDIDATE_INDEX_CONTAINS_APPROVED_PHOTO")
        rows.append({
            "taxon_key": key,
            "scientific_name": name.strip(),
            "candidate_photo_records": candidate_count,
            "link_only_source_records": link_count,
            "distinct_photo_source_records": distinct,
            "minimum_target": MINIMUM_TARGET,
            "preferred_target": PREFERRED_TARGET,
            "preferred_max_target": PREFERRED_MAX_TARGET,
            "gap_to_minimum": max(0, MINIMUM_TARGET - distinct),
            "gap_to_preferred": max(0, PREFERRED_TARGET - distinct),
            "gap_to_preferred_max": max(0, PREFERRED_MAX_TARGET - distinct),
            "rights_pending_candidate_records": candidate_count,
            "visual_review_pending_candidate_records": candidate_count,
            "unverified_pose_hints": pose_hints,
            "unverified_behaviour_hints": behaviour_hints,
            "approved_for_imagegen_records": 0,
            "review_state": "PENDING_HUMAN_REVIEW" if distinct else "NO_REFERENCE_RECORDS",
            "license_codes": json.dumps(dict(sorted(licenses.items())), ensure_ascii=False, separators=(",", ":")),
        })
    candidate_total = sum(row["candidate_photo_records"] for row in rows)
    lead_total = sum(row["link_only_source_records"] for row in rows)
    approved_total = sum(row["approved_for_imagegen_records"] for row in rows)
    if "discovered_candidate_count" in index and index["discovered_candidate_count"] != candidate_total:
        raise ValueError("PUBLIC_CANDIDATE_TOTAL_MISMATCH")
    if "unlicensed_link_research_lead_count" in index and index["unlicensed_link_research_lead_count"] != lead_total:
        raise ValueError("PUBLIC_LINK_LEAD_TOTAL_MISMATCH")
    summary = {
        "schema": REPORT_SCHEMA,
        "source_schema": SCHEMA,
        "last_cycle": index.get("last_cycle"),
        "taxa_total": len(rows),
        "taxa_with_candidate_photos": sum(row["candidate_photo_records"] > 0 for row in rows),
        "taxa_with_link_only_source_records": sum(row["link_only_source_records"] > 0 for row in rows),
        "taxa_with_no_reference_records": sum(row["distinct_photo_source_records"] == 0 for row in rows),
        "candidate_photo_records": candidate_total,
        "link_only_source_records": lead_total,
        "distinct_photo_source_records": candidate_total + lead_total,
        "taxa_below_minimum_target": sum(row["distinct_photo_source_records"] < MINIMUM_TARGET for row in rows),
        "taxa_at_or_above_preferred_target": sum(row["distinct_photo_source_records"] >= PREFERRED_TARGET for row in rows),
        "minimum_target": MINIMUM_TARGET,
        "preferred_target": PREFERRED_TARGET,
        "preferred_max_target": PREFERRED_MAX_TARGET,
        "approved_for_imagegen_records": approved_total,
        "all_candidate_photos_unapproved": approved_total == 0,
        "status": "CANDIDATE_COVERAGE_ONLY_REVIEW_PENDING",
    }
    return {"summary": summary, "species": rows}

def write_report(index_path: Path, csv_path: Path, summary_path: Path) -> dict:
    report = compile_coverage(json.loads(index_path.read_text(encoding="utf-8")))
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["species"])
    summary_path.write_text(json.dumps(report["summary"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report["summary"]

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=Path("data/index.json"))
    parser.add_argument("--csv", type=Path, default=Path("data/species_coverage.csv"))
    parser.add_argument("--summary", type=Path, default=Path("data/species_coverage_summary.json"))
    args = parser.parse_args()
    print(json.dumps(write_report(args.index, args.csv, args.summary), sort_keys=True))

if __name__ == "__main__":
    main()
