#!/usr/bin/env python3
"""Merge five public name-only GBIF evidence shards and build a safe photo queue."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

SEED_SCHEMA = "VNMV1_PUBLIC_ROSTER_TAXON_NAME_LEADS_V1"
RECORD_SCHEMA = "VNMV1_PUBLIC_ROSTER_TAXON_NAME_EVIDENCE_V1"
EXTENSION_SCHEMA = "VNMV1_PUBLIC_RESEARCH_REFERENCE_EXTENSION_V1"
SPECIES_SCHEMA = "VNMV1_PUBLIC_RESEARCH_SPECIES_SEED_V1"
MERGE_SCHEMA = "VNMV1_PUBLIC_ROSTER_TAXON_IDENTITY_MERGE_V1"
PRIVATE_KEYS = {
    "card_id", "source_card_id", "original_drive_file_id", "original_sha256",
    "sex_stage", "private_file_id", "locality", "localities", "card_mapping",
    "specimen_mapping", "drive_id", "originals"
}
NONCANONICAL_LABEL = re.compile(
    r"\b(?:unresolved|historical|hobby|possible|pending|cf\.?|aff\.?|sp\.?)\b",
    re.IGNORECASE
)

def norm(value: str) -> str:
    return " ".join(str(value or "").split()).casefold()

def candidate(record: dict) -> tuple[str, str] | None:
    query = str(record.get("queried_public_taxon_name") or "").strip()
    source = record.get("source_evidence") or {}
    if not isinstance(source, dict) or not query or NONCANONICAL_LABEL.search(query):
        return None
    if str(source.get("status", "")).upper() != "ACCEPTED":
        return None
    if str(source.get("rank", "")).upper() != "SPECIES":
        return None
    if str(source.get("matchType", "")).upper() != "EXACT":
        return None
    try:
        confidence = int(source.get("confidence", 0))
    except (TypeError, ValueError):
        return None
    canonical = str(source.get("canonicalName") or "").strip()
    usage_key = source.get("usageKey")
    if confidence < 95 or not canonical or norm(canonical) != norm(query):
        return None
    if not isinstance(usage_key, (str, int)) or not str(usage_key).strip():
        return None
    return canonical, str(usage_key).strip()

def merge(seed_path: Path, shard_dir: Path, species_path: Path,
          extension_path: Path, evidence_out: Path, extension_out: Path) -> dict:
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    base = json.loads(species_path.read_text(encoding="utf-8"))
    extension = json.loads(extension_path.read_text(encoding="utf-8"))
    if seed.get("schema") != SEED_SCHEMA or "cards" in seed:
        raise ValueError("PRIVATE_OR_INVALID_PUBLIC_NAME_SEED")
    if base.get("schema") != SPECIES_SCHEMA or "cards" in base:
        raise ValueError("PRIVATE_OR_INVALID_PUBLIC_SPECIES_SEED")
    if extension.get("schema") != EXTENSION_SCHEMA or "cards" in extension:
        raise ValueError("PRIVATE_OR_INVALID_PUBLIC_EXTENSION")
    names = seed.get("taxon_name_leads") or []
    name_keys = [norm(name) for name in names]
    if not names or len(names) != len(set(name_keys)):
        raise ValueError("INVALID_OR_DUPLICATE_ROSTER_NAME_SEED")

    records = []
    for shard in range(5):
        path = shard_dir / f"roster-identity-{shard}" / f"shard-{shard}.json"
        item = json.loads(path.read_text(encoding="utf-8"))
        if (item.get("schema") != RECORD_SCHEMA or item.get("shard") != shard
                or item.get("shard_count") != 5):
            raise ValueError(f"INVALID_SHARD_{shard}")
        expected = [name for index, name in enumerate(names) if index % 5 == shard]
        rows = item.get("records") or []
        if any(not isinstance(row, dict) for row in rows):
            raise ValueError("INVALID_EVIDENCE_RECORD")
        got = [row.get("queried_public_taxon_name") for row in rows]
        if got != expected:
            raise ValueError(f"SHARD_{shard}_COVERAGE_MISMATCH")
        for row in rows:
            if any(key in row for key in PRIVATE_KEYS):
                raise ValueError("PRIVATE_SPECIMEN_DATA_FORBIDDEN")
            if (row.get("exact_specimen_identification") is not False
                    or row.get("user_approved") is not False
                    or row.get("canonical_identity_updated") is not False):
                raise ValueError("UNAUTHORIZED_SPECIMEN_APPROVAL")
        records.extend(rows)
    if len(records) != len(names) or len({norm(row["queried_public_taxon_name"]) for row in records}) != len(names):
        raise ValueError("DUPLICATE_OR_MISSING_PUBLIC_NAME_EVIDENCE")

    manual_rows = list(extension.get("species") or [])
    if any(not isinstance(row, dict) for row in manual_rows):
        raise ValueError("INVALID_MANUAL_EXTENSION_ROWS")
    base_rows = list(base.get("species") or [])
    existing_names = {
        norm(row.get("name")) for row in base_rows + manual_rows
        if isinstance(row, dict) and row.get("name")
    }
    existing_keys = {
        str(row.get("key")) for row in base_rows + manual_rows
        if isinstance(row, dict) and row.get("key")
    }
    accepted = []
    accepted_names = set()
    eligible_matches = 0
    for record in records:
        match = candidate(record)
        if not match:
            continue
        eligible_matches += 1
        canonical, usage_key = match
        key = hashlib.sha256(("roster-gbif:" + usage_key).encode("utf-8")).hexdigest()[:16]
        canonical_key = norm(canonical)
        if canonical_key in existing_names or canonical_key in accepted_names or key in existing_keys:
            continue
        accepted_names.add(canonical_key)
        existing_keys.add(key)
        search_name = urlencode({"taxon_name": canonical})[len("taxon_name="):]
        accepted.append({
            "name": canonical,
            "key": key,
            "rank": "SPECIES",
            "taxon_status": "RESEARCH_CANDIDATE_UNVERIFIED",
            "intake_group": "Current roster exact accepted GBIF name match",
            "source_searches": [
                {
                    "label": "iNaturalist observation photos",
                    "url": "https://www.inaturalist.org/observations?" + urlencode({"taxon_name": canonical}),
                    "kind": "PHOTO_SEARCH"
                },
                {
                    "label": "Wikimedia Commons images",
                    "url": "https://commons.wikimedia.org/w/index.php?search=" + search_name + "&title=Special%3AMediaSearch&type=image",
                    "kind": "PHOTO_SEARCH"
                }
            ]
        })
    accepted.sort(key=lambda row: norm(row["name"]))
    combined_extension = {
        **extension,
        "generated_from_public_name_evidence": True,
        "species": manual_rows + accepted
    }
    evidence = {
        "schema": MERGE_SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "public_name_leads_looked_up": len(records),
        "gbif_name_responses": sum(
            row.get("research_status") == "UNVERIFIED_TAXONOMIC_NAME_LEAD" for row in records
        ),
        "source_unavailable_retry_required": sum(
            row.get("research_status") == "SOURCE_UNAVAILABLE_RETRY_REQUIRED" for row in records
        ),
        "exact_accepted_species_name_matches": eligible_matches,
        "new_photo_research_taxa_added": len(accepted),
        "actual_specimen_photos_visually_checked": 0,
        "specimen_identities_approved": 0,
        "card_mappings_exposed": False,
        "no_paid_model_api": True,
        "disclaimer": "Public taxon-name matches only. Exact accepted species matches are queued as unverified photo research candidates. No specimen photos were examined and no card mappings or identity approvals were made.",
        "records": records
    }
    evidence_out.parent.mkdir(parents=True, exist_ok=True)
    evidence_out.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    extension_out.parent.mkdir(parents=True, exist_ok=True)
    extension_out.write_text(json.dumps(combined_extension, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Merged {len(records)} public name lookups; "
        f"{len(accepted)} new exact accepted species queued; 0 specimen approvals"
    )
    return evidence

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--shards", type=Path, required=True)
    parser.add_argument("--species", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    parser.add_argument("--evidence-out", type=Path, required=True)
    parser.add_argument("--generated-extension-out", type=Path, required=True)
    args = parser.parse_args()
    merge(args.seed, args.shards, args.species, args.extension,
          args.evidence_out, args.generated_extension_out)
