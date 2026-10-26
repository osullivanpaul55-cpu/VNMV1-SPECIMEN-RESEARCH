#!/usr/bin/env python3
"""Evidence-scoped Theraphosidae measured-exemplar 3D research study.

Builds ONE geometry demonstration using published left-side measurements of
Aphonopelma eutylenum female APH_1031. It NEVER assigns measurements to
A. mooreae or to any other 587-card animal. All joint angles are hypotheses.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np
import trimesh

SEGMENTS=("coxa","trochanter","femur","patella","tibia","metatarsus","tarsus")
LEG_IDS=("I","II","III","IV")
EXEMPLAR="APH_1031"
SOURCE_TAXON="Aphonopelma eutylenum"
RIGHT_INFERRED="RIGHT_SIDE_MIRROR_OF_LEFT_REFERENCE_NOT_MEASURED"
MM_TO_METRE=.001


def load_source(path):
    source=json.loads(Path(path).read_text(encoding="utf-8"))
    if source.get("schema")!="VNMV1_THERAPHOSIDAE_SCIENTIFIC_MORPHOMETRY_EVIDENCE_V1":
        raise ValueError("MORPHOMETRY_AUTHORITY_UNKNOWN")
    source_ids={x["id"] for x in source.get("sources",[])}
    specimen=next((x for x in source["published_exemplars"] if x["id"]==EXEMPLAR),None)
    if specimen is None or specimen.get("scientific_source_id") not in source_ids:
        raise ValueError("PUBLISHED_VOUCHER_OR_SOURCE_UNBOUND")
    if specimen["taxon"]!=SOURCE_TAXON or specimen["sex"]!="adult female" or specimen["side_measured"]!="LEFT":
        raise ValueError("VOUCHER_SPECIES_SEX_OR_SIDE_CHANGED")
    if tuple(source["topology"]["segments"])!=SEGMENTS or source["topology"]["walking_legs"]!=8:
        raise ValueError("WRONG_ARANEAE_TOPOLOGY")
    if set(specimen["leg_distal_five_articles"])!={"I","III","IV"}:
        raise ValueError("MISSING_EXEMPLAR_MEASURED_LEGS")
    if not isinstance(specimen.get("carapace"),dict):
        raise ValueError("NO_PUBLISHED_CARAPACE_MEASUREMENTS")
    for leg,articles in specimen["leg_distal_five_articles"].items():
        if set(articles)!=set(SEGMENTS[2:]) or any(type(v) not in (float,int) or not math.isfinite(v) or v<=0 for v in articles.values()):
            raise ValueError("INVALID_PUBLISHED_DISTAL_FIVE:"+leg)
    return source,specimen


def make_ellipsoid(scene,name,scale_xyz,center_xyz):
    mesh=trimesh.creation.icosphere(subdivisions=1,radius=1)
    mesh.apply_scale(np.array(scale_xyz)*MM_TO_METRE)
    scene.add_geometry(mesh,geom_name=name,node_name=name,
                       transform=trimesh.transformations.translation_matrix(np.array(center_xyz)*MM_TO_METRE))


def plan_segments(specimen,side,leg):
    measured=specimen["leg_distal_five_articles"].get(leg)
    # Stated engineering placeholders only; NEVER scientific measurements.
    default_distal={"femur":11.5,"patella":5.0,"tibia":9.0,"metatarsus":9.0,"tarsus":6.0}
    values={"coxa":3.0,"trochanter":2.0,**(measured or default_distal)}
    result=[]
    for name in SEGMENTS:
        status=("PUBLISHED_MEASURED_LEFT_ARTICLE"
                if (side=="L" and measured and name in measured)
                else (RIGHT_INFERRED if side=="R" and measured and name in measured
                      else "UNMEASURED_ENGINEERING_PLACEHOLDER"))
        result.append({"article":name,"length_mm":values[name],"evidence_status":status,
                       "measurement_source":specimen["scientific_source_id"] if status=="PUBLISHED_MEASURED_LEFT_ARTICLE" else None})
    return result


def build(source,specimen):
    car=specimen["carapace"]
    scene=trimesh.Scene()
    # Carapace length and width taken from voucher. Height and abdomen unmeasured placeholders.
    make_ellipsoid(scene,"CARAPACE_PUBLISHED_LENGTH_WIDTH_UNMEASURED_HEIGHT",
                   (car["width"]/2,car["length"]/2,3.5),(0,0,8))
    make_ellipsoid(scene,"ABDOMEN_ALL_DIMENSIONS_MODELLED_NOT_MEASURED",
                   (8.5,9.5,5.5),(0,-16,8))
    make_ellipsoid(scene,"PEDICEL_UNMEASURED",(2,3,2),(0,-9,8))
    for side in (-1,1):
        mark="L" if side==-1 else "R"
        for roman in LEG_IDS:
            leg_index=LEG_IDS.index(roman)
            ident=f"{mark}_{roman}"
            root=(side*(car["width"]*.40), 4-leg_index*3.1, 8)
            pivot=f"{ident}_PROSOMA_ATTACHMENT"
            # Tiny root-marker is not an anatomical character or observed root coordinate.
            m=trimesh.creation.icosphere(subdivisions=0,radius=.00035)
            scene.add_geometry(m,geom_name=pivot,node_name=pivot,
                transform=trimesh.transformations.translation_matrix(np.array(root)*MM_TO_METRE))
            previous_length=0.
            parent=pivot
            for i,rec in enumerate(plan_segments(specimen,mark,roman)):
                length=rec["length_mm"]*MM_TO_METRE
                mesh=trimesh.creation.cylinder(
                    radius=.00075 if i<=3 else .00040,
                    segment=np.array([[0.,0.,0.],[length,0.,0.]],dtype=float),
                    sections=9)
                # Hypothetical joint rotations (not measured angles and not kinematics limits).
                theta=(0.24 if leg_index<2 else -.16)+(-.06*i if leg_index>=2 else .035*i)
                phi=.055 if i<3 else -.09
                direction=side
                rotation=trimesh.transformations.rotation_matrix(direction*theta,[0,0,1])
                tilt=trimesh.transformations.rotation_matrix(phi,[0,1,0])
                local=trimesh.transformations.translation_matrix((previous_length,0,0))@rotation@tilt
                name=f"{ident}_{rec['article'].upper()}"
                scene.add_geometry(mesh,geom_name=name,node_name=name,
                    parent_node_name=parent,transform=local)
                parent=name
                previous_length=length
        # Separate female palps; do not invent mature-male emboli.
        make_ellipsoid(scene,f"{mark}_PEDIPALP_ROOT_UNMEASURED",(1.0,2.1,1.0),
                       (side*3.8,8,6.9))
    scene.metadata={"evidence_voucher":EXEMPLAR,
                    "reference_species":SOURCE_TAXON,
                    "role":"UNCERTIFIED_MEASUREMENT_CALIBRATED_RIG_STUDY",
                    "biologically_validated_pose":False,
                    "species_specific_master":False}
    return scene


def evaluate(source,specimen):
    plans={f"{side}_{leg}":plan_segments(specimen,side,leg)
           for side in ("L","R") for leg in LEG_IDS}
    measured=[r for segs in plans.values() for r in segs if r["evidence_status"]=="PUBLISHED_MEASURED_LEFT_ARTICLE"]
    right=[r for segs in plans.values() for r in segs if r["evidence_status"]==RIGHT_INFERRED]
    return {"voucher":EXEMPLAR,"taxon":SOURCE_TAXON,"sex":"female",
            "walking_legs":len(plans),"leg_article_records":sum(map(len,plans.values())),
            "distinct_published_left_distal_article_lengths":len(measured),
            "right_equivalents_not_measured":len(right),
            "coxa_and_trochanter_lengths_measured":0,
            "three_dimensional_joint_angles_measured":0,
            "pose_and_ground_contacts_biologically_validated":False,
            "eye_spinneret_male_diagnostic_details_encoded":False,
            "family_wide_measurement_transfer_allowed":False,
            "card0016_measurement_transfer_allowed":False,
            "master_approved":False,
            "legs":plans}


def execute(source_path,outdir):
    source,specimen=load_source(source_path)
    outdir=Path(outdir)
    outdir.mkdir(parents=True,exist_ok=True)
    audit=evaluate(source,specimen)
    scene=build(source,specimen)
    payload=scene.export(file_type="glb")
    restored=trimesh.load(io.BytesIO(payload),file_type="glb",force="scene")
    nodes=set(restored.graph.nodes)
    required={f"{s}_{i}_{article.upper()}" for s in ("L","R")
              for i in LEG_IDS for article in SEGMENTS}
    if not required.issubset(nodes):
        raise RuntimeError("EXPORT_DROPPED_ANATOMICALLY_NAMED_NODES")
    if audit["distinct_published_left_distal_article_lengths"]!=15 or audit["right_equivalents_not_measured"]!=15:
        raise RuntimeError("SOURCE_SCOPE_BROKEN")
    glb=outdir/"APH_1031_FEMALE_MORPHOMETRY_ANCHORED_RESEARCH_ONLY.glb"
    glb.write_bytes(payload)
    audit["model_file"]=glb.name
    audit["model_sha256"]=hashlib.sha256(payload).hexdigest()
    audit["model_graph_named_leg_articles"]=len(required)
    audit["geometry_status"]="PUBLISHED_LEFT_ARTICLE_LENGTHS_PLUS_HYPOTHETICAL_3D_POSE"
    audit["data_source_ids"]=[x["id"] for x in source["sources"]]
    audit["card_research_scope"]="NO_PRIVATE_ORIGINAL_OR_CARD_MAPPING_CONSUMED"
    (outdir/"measured_exemplar_audit.json").write_text(json.dumps(audit,indent=2))
    return audit


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",default="research/data/theraphosidae_morphometry_evidence_v1.json")
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    a=execute(args.source,args.out)
    print(json.dumps({k:v for k,v in a.items() if k!="legs"},indent=2))
