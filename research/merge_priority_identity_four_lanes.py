#!/usr/bin/env python3
"""Merge four taxon-name evidence shards, without making specimen or approval claims."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

SEED_SCHEMA = "VNMV1_PUBLIC_PRIORITY_IDENTITY_TAXON_LEADS_V1"
RECORD_SCHEMA = "VNMV1_PUBLIC_PRIORITY_IDENTITY_NAME_EVIDENCE_V1"
MERGE_SCHEMA = "VNMV1_PUBLIC_PRIORITY_IDENTITY_EVIDENCE_MERGE_V1"

def merge(seed_file, shard_dir, out_file):
    seed = json.loads(Path(seed_file).read_text(encoding="utf-8"))
    if seed["schema"] != SEED_SCHEMA or "cards" in seed:
        raise ValueError("PRIVATE_OR_INVALID_SEED")
    all_names = seed["taxon_name_leads"]
    data = []
    for i in range(4):
        p = Path(shard_dir) / f"identity-evidence-{i}" / f"shard-{i}.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        if d["schema"] != RECORD_SCHEMA or d["shard"] != i or d["shard_count"] != 4:
            raise ValueError(f"INVALID_SHARD_{i}")
        expected = [name for j, name in enumerate(all_names) if j % 4 == i]
        got = [x["queried_public_taxon_name"] for x in d["records"]]
        if got != expected:
            raise ValueError(f"SHARD_{i}_COVERAGE_MISMATCH")
        for x in d["records"]:
            if x.get("exact_specimen_identification") is not False or x.get("user_approved") is not False or x.get("canonical_identity_updated") is not False:
                raise ValueError("UNAUTHORIZED_SPECIMEN_APPROVAL")
            if any(k in x for k in ["card_id", "original_drive_file_id", "original_sha256", "sex_stage", "private_file_id"]):
                raise ValueError("PRIVATE_SOURCE_DATA_FORBIDDEN")
        data.extend(d["records"])
    if len(data) != len(all_names) or len(set(x["queried_public_taxon_name"].casefold() for x in data)) != len(all_names):
        raise ValueError("DUPLICATE_OR_MISSING_RESEARCH_LEADS")
    evidence = {
        "schema": MERGE_SCHEMA,
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "pending_private_cards_needing_resolution": 110,
        "public_name_leads_looked_up": len(data),
        "successful_gbif_api_responses": sum(x["research_status"] == "UNVERIFIED_TAXONOMIC_NAME_LEAD" for x in data),
        "source_unavailable_retry_required": sum(x["research_status"] == "SOURCE_UNAVAILABLE_RETRY_REQUIRED" for x in data),
        "actual_specimen_photos_visually_checked": 0,
        "specimen_identities_confirmed_by_these_runners": 0,
        "user_approvals": 0,
        "card_mappings_exposed": False,
        "disclaimer": "Public species-name lookups only. No original photo or specimen examined. Keep all 110 private card identity cases for original-photo/human review until separately resolved.",
        "records": data
    }
    out = Path(out_file); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Four lanes merged: {len(data)} name leads; {evidence['successful_gbif_api_responses']} API responses; {evidence['source_unavailable_retry_required']} retryable failures; 0 specimen approvals")
    return evidence

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", default="research/priority_identity_taxon_leads.json")
    p.add_argument("--shards", required=True)
    p.add_argument("--out", default="data/priority_identity_taxon_evidence.json")
    a = p.parse_args()
    merge(a.seed, a.shards, a.out)
