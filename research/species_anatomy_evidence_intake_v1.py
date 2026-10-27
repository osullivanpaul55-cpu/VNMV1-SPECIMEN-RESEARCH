#!/usr/bin/env python3
"""Turn FIVE public photo-research shards into species-bound anatomy EVIDENCE LEADS.

Uses existing downloaded, cryptographically hashed candidate photos; NO image
inspection/pose recognition or taxonomic, sex, measurement, licence or master
approval. Must never publish private card IDs or infer sex/anatomical lengths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

SCHEMA="VNMV1_PUBLIC_SPECIES_ANATOMY_EVIDENCE_INTAKE_V1"
CANONICAL="VNMV1_SPECIES_BOUND_ANATOMY_DOCTRINE_V1"
SHA=re.compile(r"^[0-9a-f]{64}$", re.I)
RESEARCH_STATUSES={"REVIEW_REQUIRED","LINK_RESEARCH_READY","ALREADY_COLLECTED_OR_NO_NEW_LEADS","NO_CANDIDATES","RETRY_DISCOVERY"}
UNKNOWN_ARTICLES=("coxa","trochanter","femur","patella","tibia","metatarsus","tarsus")

def exact_name(t):
    return " ".join(str(t or "").split()).casefold()

def source_ok(uri):
    try:
        p=urlparse(uri)
        return p.scheme=="https" and p.hostname in {"www.inaturalist.org","www.gbif.org","commons.wikimedia.org"} and not p.username and not p.password
    except (ValueError,TypeError):
        return False

def make_row(taxon, source, media=False):
    if exact_name(source.get("taxon")) != exact_name(taxon):
        raise ValueError("CROSS_TAXON_SOURCE_CANNOT_ENTER_SPECIES_INTAKE")
    if not source_ok(source.get("source_url")):
        raise ValueError("SOURCE_URL_REQUIRED_FOR_EVIDENCE_LEAD")
    if media:
        digest=source.get("sha256")
        if not isinstance(digest,str) or not SHA.fullmatch(digest):
            raise ValueError("SOURCE_PHOTO_DIGEST_REQUIRED")
        if source.get("link_only") is True:
            raise ValueError("LINK_ONLY_SOURCE_HAS_COPIED_IMAGE")
        if not source.get("archive_member") or not source.get("observation_id"):
            raise ValueError("MEDIA_ARCHIVE_AND_OBSERVATION_PROVENANCE_REQUIRED")
    else:
        if source.get("sha256") or source.get("archive_member"):
            raise ValueError("LINK_ONLY_CAN_HAVE_NO_CACHED_PIXEL_ASSERTION")
    return {
        "research_taxon_lead":taxon,
        "source_url":source["source_url"],
        "photo_key":source.get("photo_key"),
        "observation_id":source.get("observation_id"),
        "source_quality_grade":source.get("observation_quality_grade","UNKNOWN"),
        "source_photo_sha256":source.get("sha256") if media else None,
        "archive_member":source.get("archive_member") if media else None,
        "source_pixels_previously_decoded_and_hashed_by_collector": bool(media),
        "pixels_independently_inspected_for_species_anatomy":False,
        "species_identity_human_verified":False,
        "sex_stage":"UNKNOWN",
        "camera_pose":"UNREVIEWED",
        "visible_joint_coordinates_verified":False,
        "rights_and_media_reuse_human_checked":False,
        "allowed_to_inform_scientific_anatomical_measurements":False,
        "approved_for_imagegen":False,
    }

def compile_intake(report):
    if report.get("schema")!="VNMV1_PUBLIC_PHOTO_RESEARCH_SHARD_V1":
        raise ValueError("PHOTO_SHARD_SCHEMA_MISMATCH")
    entries=report.get("species")
    if not isinstance(entries,list):
        raise ValueError("PHOTO_SHARD_SPECIES_MISSING")
    species=[]
    seen=set()
    for entry in entries:
        name=entry.get("taxon")
        key=entry.get("key")
        if not isinstance(name,str) or not name.strip() or not isinstance(key,str) or not key.strip():
            raise ValueError("INVALID_TAXON_KEY")
        if key in seen: raise ValueError("DUPLICATE_TAXON_KEY")
        seen.add(key)
        if entry.get("status") not in RESEARCH_STATUSES:
            raise ValueError("UNRECOGNIZED_RESEARCH_STATUS")
        candidates=entry.get("new_candidates") or []
        links=entry.get("new_link_leads") or []
        if any(x.get("approved_for_imagegen") is True or x.get("reviewed_by_human") is True for x in candidates+links):
            raise ValueError("PUBLIC_SOURCE_CANNOT_ASSERT_HUMAN_APPROVAL")
        references=[make_row(name,x,True) for x in candidates]
        references.extend(make_row(name,x,False) for x in links)
        species.append({
            "taxon_name_public_research_lead":name,
            "public_research_key":key,
            "source_research_status":entry.get("status"),
            "source_candidates":references,
            "separate_observation_groups":len({r["observation_id"] for r in references if r["observation_id"]}),
            "source_photographs_collected":len(candidates),
            "source_links_only":len(links),
            "specimen_species_verified":False,
            "male_female_morphology_verified":False,
            "independent_joint_review_complete":False,
            "verified_species_morphometrics":{},
            "unknown_leg_article_lengths_mm":{v:None for v in UNKNOWN_ARTICLES},
            "meshes_approved":0,
            "anatomy_evidence_profile_status":"REQUIRES_PRIVATE_IDENTITY_AND_REVIEW",
            "next_research_tasks":[
                "Confirm specimen/source taxon and human-approved sex stage",
                "Review genuine photo pixels and mark visible joints with camera angle",
                "Seek same-species published voucher morphometrics; do not rescale comparator measurements",
                "Review occluded joints, bilateral asymmetry and independent second viewpoint",
                "Independent human anatomy and source QA before model promotion",
            ],
        })
    return {
        "schema":SCHEMA,"canonical_policy":CANONICAL,
        "canonical_repository":"osullivanpaul55-cpu/VNMV1-FLUX-Docker-Build",
        "source_schema":report["schema"],
        "shard":report.get("shard"),
        "cycle":report.get("cycle"),
        "distinct_taxa_researched":len(species),
        "new_photos_hashed_but_not_anatomically_inspected":sum(s["source_photographs_collected"] for s in species),
        "human_approved_anatomical_profiles":0,"approved_3d_species_rigs":0,
        "private_card_ids_exposed":False,
        "all_numeric_anatomy_unknown_until_exact_species_source":True,
        "species":species,
    }

def build(report_path,out):
    input_bytes=Path(report_path).read_bytes()
    result=compile_intake(json.loads(input_bytes))
    result["source_report_sha256"]=hashlib.sha256(input_bytes).hexdigest()
    dest=Path(out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--report",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    result=build(a.report,a.out)
    print(json.dumps({k:result[k] for k in (
        "shard","cycle","distinct_taxa_researched",
        "new_photos_hashed_but_not_anatomically_inspected",
        "human_approved_anatomical_profiles","approved_3d_species_rigs")}))
