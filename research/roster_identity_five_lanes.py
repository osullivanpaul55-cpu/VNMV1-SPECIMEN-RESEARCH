#!/usr/bin/env python3
"""Five disjoint public taxon-name lookup lanes for the current roster labels.

This program handles names only. It never reads private card mappings, original
specimen photos, locality data, or approval state. GBIF matches are leads only.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SEED_SCHEMA = "VNMV1_PUBLIC_ROSTER_TAXON_NAME_LEADS_V1"
RESULT_SCHEMA = "VNMV1_PUBLIC_ROSTER_TAXON_NAME_EVIDENCE_V1"
SOURCE = "GBIF_SPECIES_MATCH_API"
SAFE_NAME = re.compile(r"^[\w .(),;'\"/×?–—\-:]+$", re.UNICODE)
USER_AGENT = "VNMV1-public-roster-taxonomy-research/1.0 (taxon names only)"

def load_seed(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SEED_SCHEMA:
        raise ValueError("INVALID_ROSTER_TAXON_NAME_SEED")
    if any(key in data for key in (
        "cards", "card_ids", "originals", "file_ids", "hashes",
        "specimen_mapping", "localities", "media"
    )):
        raise ValueError("PRIVATE_SPECIMEN_DATA_FORBIDDEN")
    names = data.get("taxon_name_leads")
    if not isinstance(names, list) or not 1 <= len(names) <= 600:
        raise ValueError("INVALID_TAXON_NAME_LIST")
    keys = set()
    for name in names:
        if (not isinstance(name, str) or not 3 <= len(name) <= 160
                or any(ord(ch) < 32 for ch in name) or not SAFE_NAME.fullmatch(name)):
            raise ValueError("UNSAFE_TAXON_NAME_LEAD")
        key = " ".join(name.split()).casefold()
        if key in keys:
            raise ValueError("DUPLICATE_TAXON_NAME_LEAD")
        keys.add(key)
    return names

def evidence(name: str, payload: dict) -> dict:
    fields = (
        "usageKey", "scientificName", "canonicalName", "rank", "status",
        "confidence", "matchType", "kingdom", "phylum", "class", "order",
        "family", "genus", "species", "authorship", "note", "synonym"
    )
    facts = {
        key: payload[key] for key in fields
        if key in payload and isinstance(payload[key], (str, int, float, bool))
    }
    return {
        "queried_public_taxon_name": name,
        "source": SOURCE,
        "source_url": "https://api.gbif.org/v1/species/match?" + urlencode({"name": name}),
        "source_evidence": facts,
        "research_status": "UNVERIFIED_TAXONOMIC_NAME_LEAD",
        "exact_specimen_identification": False,
        "original_photo_visually_inspected": False,
        "user_approved": False,
        "canonical_identity_updated": False,
        "needs_original_comparison": True
    }

def query_gbif(name: str) -> dict:
    url = "https://api.gbif.org/v1/species/match?" + urlencode({"name": name})
    error = None
    for attempt in range(3):
        try:
            request = Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
            )
            with urlopen(request, timeout=17) as response:
                raw = response.read(150001)
            if len(raw) > 150000:
                raise ValueError("OVERSIZED_RESPONSE")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("INVALID_GBIF_PAYLOAD")
            return evidence(name, payload)
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
            error = str(exc)[:150]
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    return {
        "queried_public_taxon_name": name,
        "source": SOURCE,
        "source_url": url,
        "research_status": "SOURCE_UNAVAILABLE_RETRY_REQUIRED",
        "error_excerpt": error,
        "exact_specimen_identification": False,
        "original_photo_visually_inspected": False,
        "user_approved": False,
        "canonical_identity_updated": False,
        "needs_original_comparison": True
    }

def run(seed_path: Path, shard: int, shard_count: int, output: Path) -> dict:
    if shard_count != 5 or not 0 <= shard < shard_count:
        raise ValueError("FIVE_SHARDS_REQUIRED")
    names = load_seed(seed_path)
    work = [name for index, name in enumerate(names) if index % shard_count == shard]
    records = []
    for name in work:
        records.append(query_gbif(name))
        time.sleep(0.35)
    result = {
        "schema": RESULT_SCHEMA,
        "shard": shard,
        "shard_count": shard_count,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "name_leads_this_shard": len(work),
        "lookups_with_a_response": sum(
            row["research_status"] != "SOURCE_UNAVAILABLE_RETRY_REQUIRED" for row in records
        ),
        "source_unavailable_retry_required": sum(
            row["research_status"] == "SOURCE_UNAVAILABLE_RETRY_REQUIRED" for row in records
        ),
        "no_paid_model_api": True,
        "no_original_photos_accessed": True,
        "no_card_identity_approval": True,
        "records": records
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Shard {shard}/{shard_count-1}: {len(work)} public names; "
        f"{result['lookups_with_a_response']} responses; "
        f"{result['source_unavailable_retry_required']} retryable failures",
        flush=True
    )
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--shard-count", type=int, default=5)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.seed, args.shard, args.shard_count, args.out)
