#!/usr/bin/env python3
"""Fail-closed validation of AI visual draft proposals against exact archived photo hashes."""
import json
import re
from pathlib import Path

POSES={"UNREVIEWED","FRONTAL","WALKING_AWAY_REAR_OBLIQUE","LATERAL_PROFILE",
       "OBLIQUE_THREE_QUARTER","DORSAL_TOP_DOWN","POSTERIOR","ELEVATED_ALERT",
       "DEFENSIVE_THREAT","VENTRAL_UNDERSIDE","VERTICAL_CLIMB"}
SEXES={"UNKNOWN","FEMALE","MATURE_MALE","JUVENILE_SUBADULT"}
STAGES={"UNKNOWN","MATURE_MALE","ADULT_FEMALE_MATURE","ADULT_FEMALE_YOUNGER",
        "JUVENILE_SPIDERLING"}
CONF={"LOW","MEDIUM","HIGH","UNKNOWN"}
SUITABILITY={"PENDING","ACCEPT_REFERENCE","STRUCTURAL_ONLY","HABITAT_ONLY","NEEDS_RESEARCH","REJECT"}
def validate(index,proposals):
    errors=[]
    if proposals.get("schema")!="VNMV1_PUBLIC_VISUAL_RECOMMENDATIONS_V1":errors.append("BAD_SCHEMA")
    if not isinstance(proposals.get("revision"),int) or proposals["revision"]<1:errors.append("BAD_REVISION")
    photos=proposals.get("photos")
    if not isinstance(photos,dict) or len(photos)>25000:return errors+["BAD_PHOTO_RECORDS"]
    known={}
    for species in index.get("species",{}).values():
        for row in species.get("candidates",[]) or []:
            if row.get("sha256"):known[row.get("photo_key")]=row.get("sha256")
    for key,p in photos.items():
        if not isinstance(p,dict) or not re.fullmatch(r"inat:\d+",key):
            errors.append(f"{key}:BAD_RECORD");continue
        if known.get(key)!=p.get("source_image_sha256"):
            errors.append(f"{key}:SOURCE_SHA_MISMATCH");continue
        if p.get("analysis_method")!="CHATGPT_VISUAL_DRAFT":
            errors.append(f"{key}:NOT_VISUAL_DRAFT")
        if p.get("reviewed_actual_image") is not True:
            errors.append(f"{key}:IMAGE_INSPECTION_NOT_ATTESTED")
        if not p.get("visible_image_notes") or len(str(p.get("visible_image_notes")))>900:
            errors.append(f"{key}:MISSING_VISUAL_NOTES")
        if p.get("recommended_pose_id") not in POSES:errors.append(f"{key}:BAD_POSE")
        if p.get("recommended_sex","UNKNOWN") not in SEXES:errors.append(f"{key}:BAD_SEX")
        if p.get("recommended_life_stage","UNKNOWN") not in STAGES:errors.append(f"{key}:BAD_STAGE")
        if p.get("confidence","UNKNOWN") not in CONF:errors.append(f"{key}:BAD_CONFIDENCE")
        if p.get("recommended_suitability","PENDING") not in SUITABILITY:
            errors.append(f"{key}:BAD_SUITABILITY")
        if p.get("recommended_suitability")=="HABITAT_ONLY":
            if p.get("specimen_visible") is not False:errors.append(f"{key}:HABITAT_SPECIMEN_CONFLICT")
            if p.get("recommended_visible_anatomy"):errors.append(f"{key}:HABITAT_ONLY_CANNOT_PROVE_ANATOMY")
            if p.get("recommended_sex")!="UNKNOWN":errors.append(f"{key}:HABITAT_ONLY_CANNOT_PROVE_SEX")
            if p.get("recommended_pose_id")!="UNREVIEWED":errors.append(f"{key}:HABITAT_ONLY_CANNOT_PROVE_POSE")
        for field in ["recommended_visible_anatomy","recommended_behaviours"]:
            tags=p.get(field,[])
            if not isinstance(tags,list) or len(tags)>56 or any(not isinstance(t,str) or len(t)>80 for t in tags):
                errors.append(f"{key}:BAD_{field}")
        if p.get("approved_for_imagegen") is not False:errors.append(f"{key}:UNSAFE_APPROVAL")
        if p.get("reviewed_by_human") is True:errors.append(f"{key}:IMPERSONATED_HUMAN")
        if p.get("resembles_original") not in (None,"NOT_ASSESSED"):
            errors.append(f"{key}:PRIVATE_ORIGINAL_NOT_INSPECTED")
    return errors
def main():
    base=Path(__file__).resolve().parents[1]
    p=json.loads((base/"data/photo_visual_reviews.json").read_text())
    index=json.loads((base/"data/index.json").read_text())
    errors=validate(index,p)
    if errors:raise SystemExit("\n".join(errors[:35]))
    print(f"Visual-draft provenance validator PASS: {len(p['photos'])} hash-bound photo draft(s)")
if __name__=="__main__":main()
