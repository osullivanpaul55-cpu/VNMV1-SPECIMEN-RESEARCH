#!/usr/bin/env python3
"""Compile a per-taxon public photo-reference report without granting approval."""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from collect import merge_seed_with_extension

SCHEMA = "VNMV1_PUBLIC_PHOTO_CANDIDATES_V1"
REPORT_SCHEMA = "VNMV1_PUBLIC_SPECIES_PHOTO_COVERAGE_V1"
MINIMUM_TARGET = 9
PREFERRED_TARGET = 12
PREFERRED_MAX_TARGET = 15
FIELDS = (
    "taxon_key", "scientific_name", "catalog_status", "in_current_catalog", "present_in_index",
    "candidate_photo_records", "index_link_only_source_records",
    "extension_curated_photo_page_leads", "link_only_source_records",
    "distinct_photo_source_records", "minimum_target", "preferred_target",
    "preferred_max_target", "gap_to_minimum", "gap_to_preferred",
    "gap_to_preferred_max", "rights_pending_records", "visual_review_pending_candidate_records",
    "unverified_pose_hints", "unverified_behaviour_hints", "search_page_count",
    "approved_for_imagegen_records", "review_state", "license_codes",
)

def compile_coverage(index: dict, seed: dict | None = None, extension: dict | None = None) -> dict:
    if not isinstance(index, dict) or index.get("schema") != SCHEMA:
        raise ValueError("INVALID_PUBLIC_PHOTO_INDEX")
    index_species = index.get("species")
    if not isinstance(index_species, dict):
        raise ValueError("INVALID_PUBLIC_SPECIES_MAP")
    catalog = {}
    if (seed is None) != (extension is None):
        raise ValueError("SEED_AND_EXTENSION_MUST_BE_PROVIDED_TOGETHER")
    if seed is not None:
        merged = merge_seed_with_extension(seed, extension)
        for row in merged["species"]:
            key = row.get("key")
            name = row.get("name")
            if not isinstance(key, str) or not key or not isinstance(name, str) or not name.strip():
                raise ValueError("INVALID_CATALOG_TAXON")
            catalog[key] = {"scientific_name": name.strip(), "catalog_status": "CURRENT_SEED_OR_EXTENSION"}
    all_keys = set(catalog) | set(index_species)
    rows = []
    for key in sorted(all_keys, key=lambda value: (str(catalog.get(value, index_species.get(value, {})).get("scientific_name", "")).casefold(), value)):
        catalog_row = catalog.get(key)
        index_row = index_species.get(key, {})
        if not isinstance(index_row, dict):
            raise ValueError("INVALID_PUBLIC_SPECIES_ROW")
        name = (catalog_row or {}).get("scientific_name") or index_row.get("scientific_name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("MISSING_PUBLIC_SCIENTIFIC_NAME")
        candidates = index_row.get("candidates", [])
        leads = index_row.get("link_only_leads", [])
        if not isinstance(candidates, list) or not isinstance(leads, list):
            raise ValueError("INVALID_REFERENCE_RECORD_LIST")
        candidate_by_key = {}
        index_lead_by_key = {}
        extension_lead_by_key = {}
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
            candidate_by_key.setdefault(photo_key, candidate)
            approved += candidate.get("approved_for_imagegen") is True
        for lead in leads:
            if not isinstance(lead, dict):
                raise ValueError("INVALID_LINK_ONLY_RECORD")
            photo_key = lead.get("photo_key")
            if not isinstance(photo_key, str) or not photo_key:
                raise ValueError("LINK_ONLY_PHOTO_KEY_REQUIRED")
            index_lead_by_key.setdefault(photo_key, lead)
        if catalog_row is not None and seed is not None:
            name_key = name.strip().casefold()
            ext_row = next((entry for entry in extension.get("species", [])
                            if str(entry.get("name", "")).strip().casefold() == name_key), None)
            if ext_row:
                for lead in ext_row.get("curated_reference_leads", []):
                    if not isinstance(lead, dict):
                        raise ValueError("INVALID_CURATED_EXTENSION_LEAD")
                    photo_key = lead.get("photo_key")
                    if not isinstance(photo_key, str) or not photo_key:
                        raise ValueError("CURATED_EXTENSION_PHOTO_KEY_REQUIRED")
                    extension_lead_by_key.setdefault(photo_key, lead)
        index_lead_by_key = {k:v for k,v in index_lead_by_key.items() if k not in candidate_by_key}
        extension_lead_by_key = {k:v for k,v in extension_lead_by_key.items()
                                 if k not in candidate_by_key and k not in index_lead_by_key}
        for record in list(candidate_by_key.values()) + list(index_lead_by_key.values()) + list(extension_lead_by_key.values()):
            licenses[str(record.get("license_code") or "UNKNOWN")] += 1
            pose = record.get("unverified_observer_text_pose_hints", [])
            behaviour = record.get("unverified_observer_behaviour_hints", [])
            pose_hints += len(pose) if isinstance(pose, list) else 0
            behaviour_hints += len(behaviour) if isinstance(behaviour, list) else 0
        candidate_count = len(candidate_by_key)
        index_link_count = len(index_lead_by_key)
        extension_link_count = len(extension_lead_by_key)
        link_count = index_link_count + extension_link_count
        distinct = candidate_count + link_count
        if approved or (catalog_row is not None and any(x.get("approved_for_imagegen") is True
                                                         for x in extension.get("species", [])
                                                         if str(x.get("name", "")).strip().casefold() == name.strip().casefold())):
            raise ValueError("PUBLIC_CANDIDATE_INDEX_CONTAINS_APPROVED_PHOTO")
        search_pages = 0
        if catalog_row is not None and seed is not None:
            name_key = name.strip().casefold()
            ext_row = next((entry for entry in extension.get("species", [])
                            if str(entry.get("name", "")).strip().casefold() == name_key), None)
            if ext_row:
                search_pages = len(ext_row.get("source_searches", []))
        in_catalog = catalog_row is not None
        present = key in index_species
        rows.append({
            "taxon_key": key, "scientific_name": name.strip(),
            "catalog_status": catalog_row["catalog_status"] if in_catalog else "INDEX_ONLY_NOT_IN_CURRENT_CATALOG",
            "in_current_catalog": in_catalog, "present_in_index": present,
            "candidate_photo_records": candidate_count,
            "index_link_only_source_records": index_link_count,
            "extension_curated_photo_page_leads": extension_link_count,
            "link_only_source_records": link_count,
            "distinct_photo_source_records": distinct,
            "minimum_target": MINIMUM_TARGET, "preferred_target": PREFERRED_TARGET,
            "preferred_max_target": PREFERRED_MAX_TARGET,
            "gap_to_minimum": max(0, MINIMUM_TARGET - distinct),
            "gap_to_preferred": max(0, PREFERRED_TARGET - distinct),
            "gap_to_preferred_max": max(0, PREFERRED_MAX_TARGET - distinct),
            "rights_pending_records": candidate_count + link_count,
            "visual_review_pending_candidate_records": candidate_count,
            "unverified_pose_hints": pose_hints, "unverified_behaviour_hints": behaviour_hints,
            "search_page_count": search_pages, "approved_for_imagegen_records": 0,
            "review_state": ("PENDING_HUMAN_REVIEW" if distinct else
                             "NO_REFERENCE_RECORDS" if present else "NOT_YET_IN_INDEX"),
            "license_codes": json.dumps(dict(sorted(licenses.items())), ensure_ascii=False, separators=(",", ":")),
        })
    candidate_total = sum(row["candidate_photo_records"] for row in rows)
    index_link_total = sum(row["index_link_only_source_records"] for row in rows)
    ext_link_total = sum(row["extension_curated_photo_page_leads"] for row in rows)
    link_total = index_link_total + ext_link_total
    approved_total = sum(row["approved_for_imagegen_records"] for row in rows)
    if "discovered_candidate_count" in index and index["discovered_candidate_count"] != candidate_total:
        raise ValueError("PUBLIC_CANDIDATE_TOTAL_MISMATCH")
    if "unlicensed_link_research_lead_count" in index and index["unlicensed_link_research_lead_count"] != index_link_total:
        raise ValueError("PUBLIC_LINK_LEAD_TOTAL_MISMATCH")
    catalog_total = len(catalog) if seed is not None else len(rows)
    catalog_missing = sum(row["in_current_catalog"] and not row["present_in_index"] for row in rows)
    index_only = sum(not row["in_current_catalog"] for row in rows)
    unresolved = extension.get("unresolved_research_units", []) if extension is not None else []
    summary = {
        "schema": REPORT_SCHEMA, "source_schema": SCHEMA,
        "last_cycle": index.get("last_cycle"),
        "catalog_taxa_total": catalog_total, "index_taxa_total": len(index_species),
        "taxa_total": len(rows), "catalog_taxa_missing_from_index": catalog_missing,
        "index_only_taxa_total": index_only,
        "taxa_with_candidate_photos": sum(row["candidate_photo_records"] > 0 for row in rows),
        "taxa_with_link_only_source_records": sum(row["link_only_source_records"] > 0 for row in rows),
        "taxa_with_no_reference_records": sum(row["distinct_photo_source_records"] == 0 for row in rows),
        "index_candidate_photo_records": candidate_total,
        "index_link_only_source_records": index_link_total,
        "extension_curated_photo_page_leads": ext_link_total,
        "candidate_photo_records": candidate_total,
        "link_only_source_records": link_total,
        "distinct_photo_source_records": candidate_total + link_total,
        "unresolved_extension_research_units": len(unresolved),
        "unresolved_extension_search_pages": sum(len(row.get("source_searches", [])) for row in unresolved),
        "taxa_below_minimum_target": sum(row["distinct_photo_source_records"] < MINIMUM_TARGET for row in rows if row["in_current_catalog"]),
        "taxa_at_or_above_preferred_target": sum(row["distinct_photo_source_records"] >= PREFERRED_TARGET for row in rows if row["in_current_catalog"]),
        "minimum_target": MINIMUM_TARGET, "preferred_target": PREFERRED_TARGET,
        "preferred_max_target": PREFERRED_MAX_TARGET,
        "approved_for_imagegen_records": approved_total,
        "all_candidate_photos_unapproved": approved_total == 0,
        "status": "CANDIDATE_COVERAGE_ONLY_REVIEW_PENDING",
    }
    return {"summary": summary, "species": rows, "catalog": {"species": [{"key":k,**v} for k,v in sorted(catalog.items())]}}

def write_report(index_path: Path, csv_path: Path, summary_path: Path, seed_path: Path | None = None,
                 extension_path: Path | None = None) -> dict:
    if (seed_path is None) != (extension_path is None):
        raise ValueError("SEED_AND_EXTENSION_PATHS_MUST_BE_PROVIDED_TOGETHER")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    seed = json.loads(seed_path.read_text(encoding="utf-8")) if seed_path else None
    extension = json.loads(extension_path.read_text(encoding="utf-8")) if extension_path else None
    report = compile_coverage(index, seed, extension)
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
    parser.add_argument("--seed", type=Path, default=Path("research/species_seed.json"))
    parser.add_argument("--extension", type=Path, default=Path("research/species_reference_extension.json"))
    parser.add_argument("--csv", type=Path, default=Path("data/species_coverage.csv"))
    parser.add_argument("--summary", type=Path, default=Path("data/species_coverage_summary.json"))
    args = parser.parse_args()
    print(json.dumps(write_report(args.index, args.csv, args.summary, args.seed, args.extension), sort_keys=True))

if __name__ == "__main__":
    main()
