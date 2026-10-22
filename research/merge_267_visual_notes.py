#!/usr/bin/env python3
"""Merge 267 visually inspected public source-preview reviews with existing records.

The annotated input is a human-readable line-per-photo inspection compressed as
base85+zlib. Record identity derives ONLY from the source photo index. The
order/digest is pinned to the inspected 23 contact-sheet manifests, so any
index change fails instead of silently assigning labels to different photos.
This is not a model-inference process, specimen-sex verdict, or production approval.
"""
import base64
import hashlib
import json
import re
import sys
import zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"research"))
from visual_review_queue import entries

EXPECTED_ORDER_SHA="dd84962830b2276e584dbb736ce77903ccd11c0928a63df12e07856225e5887a"
POSE={"U":"UNREVIEWED","D":"DORSAL_TOP_DOWN","O":"OBLIQUE_THREE_QUARTER",
      "L":"LATERAL_PROFILE","F":"FRONTAL","V":"VENTRAL_UNDERSIDE",
      "X":"VERTICAL_CLIMB","R":"POSTERIOR"}
SUIT={"A":"ACCEPT_REFERENCE","S":"STRUCTURAL_ONLY",
      "N":"NEEDS_RESEARCH","H":"HABITAT_ONLY"}
CONF={"H":"HIGH","M":"MEDIUM","L":"LOW"}
def main():
    index=json.loads((ROOT/"data/index.json").read_text())
    reviews_path=ROOT/"data/photo_visual_reviews.json"
    archive=json.loads(reviews_path.read_text())
    if archive.get("schema")!="VNMV1_PUBLIC_VISUAL_RECOMMENDATIONS_V1":
        raise RuntimeError("Unexpected review schema")
    allphotos=entries(index)
    reviewed=archive.get("photos",{})
    pending=[x for x in allphotos if not (
        isinstance(reviewed.get(x["photo_key"]),dict)
        and reviewed[x["photo_key"]].get("source_image_sha256")==x["source_image_sha256"]
        and reviewed[x["photo_key"]].get("reviewed_actual_image") is True
        and reviewed[x["photo_key"]].get("analysis_method")=="CHATGPT_VISUAL_DRAFT"
    )]
    if len(allphotos)!=387 or len(reviewed)!=120 or len(pending)!=267:
        raise RuntimeError(f"Unexpected counts all={len(allphotos)} reviewed={len(reviewed)} pending={len(pending)}")
    actual_order=hashlib.sha256("\n".join(
        x["photo_key"]+":"+x["source_image_sha256"] for x in pending
    ).encode()).hexdigest()
    if actual_order!=EXPECTED_ORDER_SHA:
        raise RuntimeError(f"Source/ordering drift! got {actual_order}")
    raw=base64.b85decode((ROOT/"research/photo_267_visual_notes.b85").read_text().strip())
    annotated=zlib.decompress(raw).decode("utf-8")
    groups={}
    slot=None
    for line in annotated.splitlines():
        if line.startswith("##"):
            slot=int(line[2:]);groups[slot]=[]
        elif line.strip():
            if slot is None:raise RuntimeError("Annotation without sheet")
            groups[slot].append(line)
    if list(groups)!=list(range(23)):raise RuntimeError("Sheet numbering changed")
    lines=[]
    for i in range(23):
        required=3 if i==22 else 12
        if len(groups[i])!=required:raise RuntimeError(f"Sheet {i}: {len(groups[i])} != {required}")
        lines.extend(groups[i])
    if len(lines)!=267:raise RuntimeError("Missing photo reviews")
    for item,row in zip(pending,lines):
        m=re.fullmatch(r"([UDOLFVXR]) ([ASNH]) ([HML]):(.{12,900})",row)
        if not m:raise RuntimeError(f"Unrecognised row: {row[:120]}")
        pose,suit,conf,note=m.groups()
        note=note.strip()
        if suit=="H" and pose!="U":raise RuntimeError("Habitat-only cannot have species pose")
        if item["photo_key"] in reviewed:raise RuntimeError("Unsafe prior overwrite")
        taxon=item["scientific_name"]
        species_visible=suit!="H" and not (
            suit=="N" and any(t in note.lower() for t in
                 ["not distinguishable","not confidently distinguishable","no confidently identifiable"])
        )
        if not species_visible:anatomy=[]
        elif suit=="N":anatomy=["PARTIAL_BODY_SILHOUETTE"]
        elif taxon.startswith("Heterometrus"):
            anatomy=["CHELAE","SEGMENTED_BODY"]
            if any(k in note.lower() for k in ("tail","metasoma","stinger")):
                anatomy.append("METASOMA")
        elif taxon.startswith("Heteropoda"):
            anatomy=["LATERIGRADE_LEGS","HAIR_TEXTURE","BODY_SHAPE"]
        elif taxon.startswith("Hogna"):
            anatomy=["CARAPACE","LEGS","ABDOMEN"] if suit=="A" else ["BODY_PARTLY_VISIBLE"]
        elif taxon.startswith("Eresus"):
            anatomy=["VELVET_ABDOMEN","SHORT_STOUT_LEGS"] if suit=="A" else ["BODY_PARTLY_VISIBLE"]
        elif suit=="A":
            anatomy=["LEGS","CARAPACE","ABDOMEN"] if "cropped" not in note.lower() else ["FRONT_BODY","LEGS"]
        else:
            anatomy=["BODY_PARTLY_VISIBLE","LEGS_PARTLY_VISIBLE"]
        behaviour=[]
        if "spiderlings" in note.lower() and "carrying" in note.lower():
            behaviour=["SPIDERLINGS_CARRIED_DORSALLY"]
        rec={
            "analysis_method":"CHATGPT_VISUAL_DRAFT",
            "reviewed_actual_image":True,
            "inspection_medium":"PUBLIC_SOURCE_PREVIEW_CONTACT_SHEET",
            "source_image_sha256":item["source_image_sha256"],
            "reviewed_source_photo_id":item["photo_key"].split(":",1)[1],
            "scientific_name_research_label":taxon,
            "recommended_pose_id":POSE[pose],
            "recommended_suitability":SUIT[suit],
            "recommended_sex":"UNKNOWN",
            "recommended_life_stage":"UNKNOWN",
            "recommended_visible_anatomy":anatomy,
            "recommended_behaviours":behaviour,
            "confidence":CONF[conf],
            "visible_image_notes":note,
            "recommended_visual_notes":note,
            "recommended_resemblance":"NOT_ASSESSED",
            "resembles_original":"NOT_ASSESSED",
            "specimen_visible":species_visible,
            "suitability_recommendation_status":"AI_VISUAL_PROVISIONAL_NOT_HUMAN_APPROVED",
            "reference_use_status":"RESEARCH_PROPOSAL_ONLY",
            "reviewed_by_human":False,
            "approved_for_imagegen":False,
            "fine_morphology_verified":False,
            "rights_checked":False,
            "limitations":"Contact-sheet public image inspection; exact archive SHA from research index, not independently rehashed from displayed preview; sex, species identity and private original resemblance not verified."
        }
        if suit=="H":
            rec["recommended_visible_anatomy"]=[]
            rec["recommended_pose_id"]="UNREVIEWED"
            rec["recommended_sex"]="UNKNOWN"
        reviewed[item["photo_key"]]=rec
    archive["photos"]=reviewed
    archive["revision"]=int(archive.get("revision",10))+1
    archive["status"]="ALL_387_PUBLIC_CONTACT_SHEET_VISUAL_DRAFTS_READY_FOR_USER_CORRECTION"
    archive["notes"]="387/387 indexed public photo references have draft visual assessments at available preview/contact-sheet resolution. 267 new per-photo notes added; 120 previous analyses preserved. No user approvals, reliable sex claims or private-original resemblance comparisons inferred."
    from validate_visual_reviews import validate
    errors=validate(index,archive)
    if errors:raise RuntimeError("Validation rejected:\n"+"\n".join(errors[:30]))
    reviews_path.write_text(json.dumps(archive,indent=2,ensure_ascii=False)+"\n")
    print(f"PASS: {len(reviewed)}/{len(allphotos)} visual draft records; revision {archive['revision']}; no original review overwritten")
if __name__=="__main__":main()
