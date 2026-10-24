#!/usr/bin/env python3
"""Four public, disjoint research-only taxon name lanes for the 110 pending identity cases.

This script sees NO card mapping, originals, private Drive pointers, sex assignments or
Human Gold annotations. A GBIF name lookup is NEVER proof of the specimen identity.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SEED_SCHEMA = "VNMV1_PUBLIC_PRIORITY_IDENTITY_TAXON_LEADS_V1"
RESULT_SCHEMA = "VNMV1_PUBLIC_PRIORITY_IDENTITY_NAME_EVIDENCE_V1"
SOURCE = "GBIF_SPECIES_MATCH_API"
SAFE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9 .()'\-]+$")
USER_AGENT = "VNMV1-public-taxonomy-research/1.0 (public source leads only, no specimen identification)"

def load_seed(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SEED_SCHEMA:
        raise ValueError("INVALID_IDENTITY_SEED_SCHEMA")
    if any(k in data for k in ("cards", "card_ids", "originals", "file_ids", "hashes", "specimen_mapping")):
        raise ValueError("PRIVATE_SPECIMEN_MAPPING_FORBIDDEN")
    names = data.get("taxon_name_leads", [])
    if not isinstance(names, list) or len(names) > 250:
        raise ValueError("INVALID_TAXON_NAME_LIST")
    if len(names) != len(set(x.casefold() for x in names if isinstance(x, str))):
        raise ValueError("DUPLICATE_TAXON_LEAD")
    for name in names:
        if not isinstance(name, str) or not 3 <= len(name) <= 120 or not SAFE_NAME.fullmatch(name):
            raise ValueError("UNSAFE_TAXON_LEAD")
    return names

def safe_name_evidence(name: str, data: dict) -> dict:
    # GBIF names are research leads; hobby labels and synonyms require later expert review.
    fields = ["usageKey", "scientificName", "canonicalName", "rank", "status",
              "confidence", "matchType", "kingdom", "phylum", "class",
              "order", "family", "genus", "species", "authorship",
              "note", "synonym"]
    facts = {key: data[key] for key in fields if key in data and
             isinstance(data[key], (str, int, float, bool))}
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

def query_gbif(name: str):
    url = "https://api.gbif.org/v1/species/match?" + urlencode({"name": name})
    last = None
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(req, timeout=17) as response:
                raw = response.read(150001)
            if len(raw) > 150000:
                raise ValueError("OVERSIZED_RESPONSE")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("INVALID_GBIF_PAYLOAD")
            return safe_name_evidence(name, payload)
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
            last = str(exc)[:150]
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    return {
        "queried_public_taxon_name": name,
        "source": SOURCE,
        "source_url": url,
        "research_status": "SOURCE_UNAVAILABLE_RETRY_REQUIRED",
        "error_excerpt": last,
        "exact_specimen_identification": False,
        "original_photo_visually_inspected": False,
        "user_approved": False,
        "canonical_identity_updated": False
    }

def run(seed_path: Path, shard: int, output: Path, fetch=query_gbif):
    if not 0 <= shard < 4:
        raise ValueError("SHARD_MUST_BE_0_1_2_OR_3")
    names = load_seed(seed_path)
    work = [name for i, name in enumerate(names) if i % 4 == shard]
    records = []
    for name in work:
        records.append(fetch(name))
        if fetch is query_gbif:
            time.sleep(.35)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": RESULT_SCHEMA,
        "shard": shard,
        "shard_count": 4,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "leads_this_shard": len(work),
        "lookups_with_a_response": sum(x["research_status"] != "SOURCE_UNAVAILABLE_RETRY_REQUIRED" for x in records),
        "missing_or_failed": sum(x["research_status"] == "SOURCE_UNAVAILABLE_RETRY_REQUIRED" for x in records),
        "no_paid_model_api": True,
        "no_original_photos_accessed": True,
        "no_card_identity_approval": True,
        "records": records,
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Shard {shard}/3: {len(work)} name leads, "
          f"{payload['lookups_with_a_response']} name lookups with a response; "
          f"{payload['missing_or_failed']} retry needed")
    return payload

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=Path, default=Path("research/priority_identity_taxon_leads.json"))
    p.add_argument("--shard", type=int, choices=range(4), required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    run(args.seed, args.shard, args.out)
