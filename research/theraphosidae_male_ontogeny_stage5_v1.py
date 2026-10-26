#!/usr/bin/env python3
"""Stage 5: source-measured mature-male rigs and separate ontogeny research holds.

No 3D joint angles or sex-specific genital surface geometry are observed.
The exported GLBs are scientific-measurement inputs, NOT approved animal meshes.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import numpy as np
import trimesh

ARTICLES=("coxa","trochanter","femur","patella","tibia","metatarsus","tarsus")
DISTAL=ARTICLES[2:]
LEGS=("I","II","III","IV")
SCHEMA="VNMV1_THERAPHOSIDAE_MALE_ONTOGENY_EVIDENCE_V1"

def load_male(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema")!=SCHEMA or len(data.get("adult_male_vouchers",[]))!=2:
        raise ValueError("INVALID_MALE_SOURCE_SET")
    source_ids={s["id"] for s in data["sources"]}
    species=set()
    for v in data["adult_male_vouchers"]:
        if v["id"] in species or v["source_id"] not in source_ids:
            raise ValueError("MISSING_PUBLISHED_REFERENCE")
        species.add(v["id"])
        if v["sex"]!="MATURE_MALE" or v["family"]!="Theraphosidae":
            raise ValueError("SEX_OR_FAMILY_NOT_VERIFIED")
        if set(v["left_leg_distal_articles"]) not in ({"I","III","IV"},set(LEGS)):
            raise ValueError("UNEXPECTED_MEASURED_LEG_KEYS")
        for leg, measured in v["left_leg_distal_articles"].items():
            if set(measured)!=set(DISTAL) or any(type(x) not in (float,int) or not math.isfinite(x) or x<=0 for x in measured.values()):
                raise ValueError("INVALID_SOURCE_MEASUREMENT")
        if v["measured_side"] not in ("LEFT","SOURCE_SIDE_NOT_SPECIFIED"):
            raise ValueError("SOURCE_SIDE_NOT_EVIDENCED")
        if v["carapace"]["length"]<=0 or v["carapace"]["width"]<=0:
            raise ValueError("INVALID_CARAPACE")
        if v["id"]=="ZFSQ-i11578" and v["diagnostics"]["leg_I_tibial_apophysis"]!="ABSENT_PUBLISHED":
            raise ValueError("DIAGNOSTIC_APOPHYSIS_CHANGED")
    holds=data["hard_gates"]
    if any(holds[k] is not True for k in (
         "never_reuse_distal_lengths_as_other_species_measurements",
         "never_model_male_palp_bulb_without_individual_species_evidence",
         "no_juvenile_or_spiderling_mesh_from_uniform_adult_scale",
         "no_Card_0016_mooreae_edits")):
        raise ValueError("SCIENTIFIC_NONTRANSFER_POLICY_MISSING")
    return data

def female_record(path,sex_species):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    match=[x for x in data["exemplars"] if x["name"]==sex_species and x["sex"]=="FEMALE_ADULT"]
    if len(match)!=1: raise ValueError("PAIRED_FEMALE_EVIDENCE_ABSENT")
    return match[0]

def compare_same_species(male,female):
    if male["taxon"]!=female["name"]: raise ValueError("NOT_SAME_SPECIES")
    if male["comparison_female_voucher"]!=female["id"]:
        raise ValueError("FEMALE_VOUCHER_MISMATCH")
    rows=[]
    for limb in ("I","III","IV"):
        m=male["left_leg_distal_articles"][limb]
        f=female["legs"][limb]
        if not f: raise ValueError("MISSING_FEMALE_DISTAL_SERIES")
        for article in DISTAL:
            male_fraction=m[article]/male["carapace"]["length"]
            female_fraction=f[article]/female["carapace"]["length"]
            rows.append({"taxon":male["taxon"],"male_voucher":male["id"],
                         "female_voucher":female["id"],"leg":limb,"article":article,
                         "male_segment_mm":m[article],"female_segment_mm":f[article],
                         "male_segment_per_carapace":round(male_fraction,6),
                         "female_segment_per_carapace":round(female_fraction,6),
                         "male_female_relative_ratio":round(male_fraction/female_fraction,6),
                         "interpretation":"TWO_DIFFERENT_INDIVIDUALS_NOT_SEX_WIDE_NORM"})
    return rows

def add_ellipse(scene,name,center,size):
    mesh=trimesh.creation.icosphere(subdivisions=1)
    mesh.apply_scale(np.asarray(size)*.001)
    scene.add_geometry(mesh,geom_name=name,node_name=name,
        transform=trimesh.transformations.translation_matrix(np.asarray(center)*.001))

def model(male):
    scene=trimesh.Scene()
    c=male["carapace"]
    add_ellipse(scene,"MALE_CARAPACE_MEASURED_LENGTH_WIDTH_UNMEASURED_DEPTH",
                (0,0,9),(c["width"]/2,c["length"]/2,3.5))
    add_ellipse(scene,"MALE_ABDOMEN_UNMEASURED_PLACEHOLDER",
                (0,-c["length"],9),(.34*c["width"],.5*c["length"],4))
    limb_records=[]
    for sign in (-1,1):
        side="L" if sign==-1 else "R"
        for i,leg in enumerate(LEGS):
            series=male["left_leg_distal_articles"].get(leg)
            rest={a:c["length"]*v for a,v in zip(DISTAL,(.75,.37,.68,.72,.42))}
            lengths={"coxa":c["length"]*.20,"trochanter":c["length"]*.12,
                     **(series or rest)}
            anchor=f"{side}_{leg}_ROOT_UNMEASURED"
            root=(sign*c["width"]*.40,c["length"]*(.35-i*.19),9)
            tiny=trimesh.creation.icosphere(radius=.00035,subdivisions=0)
            scene.add_geometry(tiny,geom_name=anchor,node_name=anchor,
                transform=trimesh.transformations.translation_matrix(np.array(root)*.001))
            parent=anchor
            prior=0
            for k,seg in enumerate(ARTICLES):
                length=lengths[seg]*.001
                tube=trimesh.creation.cylinder(
                    radius=.0005 if k>4 else .0008,
                    segment=np.asarray([[0,0,0],[length,0,0]],dtype=float),sections=7)
                # Pose angles are hypothetical visual debugging conveniences, not from source.
                orientation=trimesh.transformations.rotation_matrix(
                    sign*(.06 if i<2 else -.055),[0,0,1])
                transform=trimesh.transformations.translation_matrix((prior,0,0))@orientation
                node=f"{side}_{leg}_{seg.upper()}"
                scene.add_geometry(tube,geom_name=node,node_name=node,parent_node_name=parent,transform=transform)
                if seg in DISTAL and series:
                    evidence=("MEASURED_PUBLISHED_LEFT" if side=="L" and male["measured_side"]=="LEFT"
                             else "PUBLISHED_SEGMENT_SIDE_NOT_REPORTED_IN_SOURCE" if side=="L"
                             else "MODEL_BILATERAL_COPY_NOT_MEASURED")
                else:
                    evidence="ARTIST_GENERIC_PLACEHOLDER_NOT_MEASURED"
                limb_records.append({"node":node,"value_mm":lengths[seg],"evidence":evidence})
                prior=length
                parent=node
        # Male palp articles are separate from walking legs. Do not create a bulb or embolus!
        parent_name=f"{side}_PALP_ROOT"
        add_ellipse(scene,parent_name,(sign*c["width"]*.23,c["length"]*.45,7),
                    (1.2,1.2,1.0))
        palp=male["palp"]
        if "femur" in palp:
            ordered=(("FEMUR",palp["femur"]),("PATELLA",palp["patella"]),
                     ("TIBIA",palp["tibia"]),("TARSUS",palp["tarsus"]))
        else:
            ordered=(("FEMUR",c["length"]*.38),("PATELLA",c["length"]*.20),
                     ("TIBIA",palp["retrolateral_tibia_length"]),
                     ("TARSUS",c["length"]*.18))
        prior=0
        for lab,length in ordered:
            tube=trimesh.creation.cylinder(
                radius=.00055,segment=np.array([[0.,0.,0.],[length*.001,0.,0.]]),sections=7)
            name=f"{side}_PALP_{lab}_NO_BULB_RECONSTRUCTION"
            scene.add_geometry(tube,geom_name=name,node_name=name,
                parent_node_name=parent_name,
                transform=trimesh.transformations.translation_matrix((prior,0,0)))
            parent_name=name;prior=length*.001
    scene.metadata={"role":"UNCERTIFIED_MATURE_MALE_GEOMETRIC_STUDY",
                    "source_male_voucher":male["id"],"source_species":male["taxon"],
                    "male_bulb_mesh_included":False,"real_3d_pose_verified":False,
                    "mature_male_tibial_apophysis_mesh_included":False,
                    "eligible_for_original_card_production":False}
    return scene,limb_records

def run(male_source,female_source,out):
    evidence=load_male(male_source)
    males=evidence["adult_male_vouchers"]
    female=female_record(female_source,"Aphonopelma chalcodes")
    paired=next(v for v in males if v["taxon"]=="Aphonopelma chalcodes")
    comparisons=compare_same_species(paired,female)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    model_reports=[]
    for male in males:
        scene,record=model(male)
        glb=scene.export(file_type="glb")
        loaded=trimesh.load(io.BytesIO(glb),file_type="glb",force="scene")
        required={f"{s}_{l}_{a.upper()}" for s in ("L","R") for l in LEGS for a in ARTICLES}
        if not required.issubset(set(loaded.graph.nodes)):
            raise RuntimeError("SEGMENT_NODE_LOST_DURING_EXPORT")
        measured=sum(1 for x in record if x["evidence"]=="MEASURED_PUBLISHED_LEFT")
        sideless=sum(1 for x in record if x["evidence"]=="PUBLISHED_SEGMENT_SIDE_NOT_REPORTED_IN_SOURCE")
        expected=len(male["left_leg_distal_articles"])*5
        if measured+sideless!=expected:
            raise RuntimeError("PROVENANCE_ARTICLE_COUNT_MISMATCH")
        name=male["id"].replace("-","_")+"_MATURE_MALE_MEASUREMENT_STUDY_NOT_MASTER.glb"
        (out/name).write_bytes(glb)
        model_reports.append({"male_voucher":male["id"],"taxon":male["taxon"],"file":name,
            "sha256":hashlib.sha256(glb).hexdigest(),"walking_leg_segments":56,
            "reported_left_segments":measured,"published_side_unspecified_segments":sideless,
            "no_emobolus_or_bulb_modelled":True,"joint_angles_evidence":"NONE",
            "reconstructable_species_anatomy":"NOT_CERTIFIED"})
    camera_angles=("FRONTAL","WALKING_AWAY_REAR_OBLIQUE","LATERAL_PROFILE",
                   "OBLIQUE_THREE_QUARTER","DORSAL_TOP_DOWN","POSTERIOR")
    queues=[]
    for male in males:
        for camera in camera_angles:
            queues.append({"voucher":male["id"],"taxon":male["taxon"],"camera":camera,
              "source_photo_coverage":"UNREVIEWED","real_projection_accuracy":"UNTESTED",
              "limb_joint_positions_from_photo":"UNAVAILABLE",
              "scientific_model_pass":False})
    for sex_stage in evidence["ontogeny"]["controlled_biological_stages"][:3]:
        queues.append({"sex_stage":sex_stage,"taxon":"THERAPHOSIDAE_RESEARCH_UNIT",
                       "camera":"ALL","source_photo_coverage":"SPECIES_STAGE_MEASUREMENT_REQUIRED",
                       "real_projection_accuracy":"UNTESTED","scientific_model_pass":False})
    report={"schema":"VNMV1_MALE_ONTOGENY_STAGE5_RESULT_V1",
       "adult_male_voucher_count":len(males),"measured_male_distal_segments":sum(len(m["left_leg_distal_articles"])*5 for m in males),
       "same_species_sex_pair":"Aphonopelma chalcodes",
       "same_species_comparative_segment_records":len(comparisons),
       "different_individuals_not_a_population_sample":True,
       "adult_male_models":model_reports,"comparisons":comparisons,
       "developmental_evidence":evidence["ontogeny"],
       "research_and_camera_evidence_queue":queues,
       "mature_male_bulb_geometry_validated":False,"life_stage_meshes_constructed":0,
       "species_anatomy_approved":0,"real_multi_angle_source_review_complete":False,
       "card0016_unchanged_required":True,
       "scope":"HISTORICAL_PRIMARY_MALE_MEASUREMENTS_PLUS_UNVERIFIED_3D_MODELLED_POSES"}
    (out/"evidence_and_sex_stage_review.json").write_text(json.dumps(report,indent=2))
    with (out/"chalcodes_male_vs_female_vouchers.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(comparisons[0]));writer.writeheader();writer.writerows(comparisons)
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--male-source",default="research/data/theraphosidae_male_ontogeny_evidence_v1.json")
    p.add_argument("--female-source",default="research/data/theraphosidae_three_females_comparison_v1.json")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    r=run(a.male_source,a.female_source,a.out)
    print(json.dumps({k:v for k,v in r.items() if k not in
         ("comparisons","developmental_evidence","research_and_camera_evidence_queue")},indent=2))
