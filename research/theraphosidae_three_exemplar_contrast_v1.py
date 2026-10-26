#!/usr/bin/env python3
"""Published 3-specimen Theraphosidae proportions comparison and illustrative GLBs.

The GLBs use real published distal limb lengths, but their 3D directions,
right limbs, proximal coxa/trochanter and all limb contacts are modelling guesses.
NEVER promote them to species, family, sex or original-card masters.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np
import trimesh

ARTICLES=("femur","patella","tibia","metatarsus","tarsus")
LEG_NUMERALS=("I","II","III","IV")
PROXIMAL=("coxa","trochanter")
SOURCE_SCHEMA="VNMV1_THERAPHOSIDAE_MULTI_EXEMPLAR_MORPHOMETRY_V1"

def load(source_path):
    data=json.loads(Path(source_path).read_text(encoding="utf-8"))
    if data.get("schema")!=SOURCE_SCHEMA: raise ValueError("UNRECOGNIZED_SOURCE_SCHEMA")
    ids={v["id"] for v in data["scientific_evidence"]}
    if len(data.get("exemplars",[]))!=3: raise ValueError("REQUIRE_THREE_PUBLISHED_EXEMPLARS")
    assert len({v["name"] for v in data["exemplars"]})==3
    for rec in data["exemplars"]:
        if rec["source"] not in ids or rec["sex"]!="FEMALE_ADULT": raise ValueError("UNBOUND_SOURCE_OR_SEX")
        if rec["carapace"]["length"]<=0 or rec["carapace"]["width"]<=0: raise ValueError("CARAPACE_INVALID")
        if set(rec["legs"])!=set(LEG_NUMERALS): raise ValueError("LEG_KEYS_INVALID")
        if rec["measurement_side"] not in ("LEFT","PUBLICATION_NOT_EXPLICITLY_RECORDED"):
            raise ValueError("SOURCE_MEASUREMENT_SIDE_INVALID")
        for key in LEG_NUMERALS:
            values=rec["legs"][key]
            if values is None:
                if key!="II" or rec["measurement_side"]!="LEFT":
                    raise ValueError("UNSUPPORTED_MISSING_MEASUREMENT")
                continue
            if set(values)!=set(ARTICLES):
                raise ValueError("SEGMENT_ORDER_MISMATCH")
            if any(type(v) not in (float,int) or not math.isfinite(v) or v<=0 for v in values.values()):
                raise ValueError("INVALID_PUBLISHED_LENGTH")
    if data["geometry_discipline"]["no_transfer_to_card0016"] is not True:
        raise ValueError("CARD0016_NONTRANSFER_GATE_MISSING")
    return data

def normalized(records):
    entries=[]
    for rec in records:
        c=rec["carapace"]["length"]
        for limb in LEG_NUMERALS:
            a=rec["legs"][limb]
            if a is None:continue
            row={"specimen_id":rec["id"],"taxon":rec["name"],"sex":rec["sex"],
                 "leg":limb,"published_article_lengths_mm":a,
                 "distal_leg_total_mm":round(sum(a.values()),4),
                 "leg_five_article_total_over_carapace_length":round(sum(a.values())/c,6),
                 "article_over_femur":{k:round(a[k]/a["femur"],6) for k in ARTICLES},
                 "source_measurement_side":rec["measurement_side"]}
            entries.append(row)
    return entries

def compare_ratio_span(rows):
    metrics=[]
    for leg in ("I","III","IV"):
        comparable=[r for r in rows if r["leg"]==leg]
        if len(comparable)!=3:raise ValueError("INSUFFICIENT_EXEMPLAR_OVERLAP")
        for a in ARTICLES[1:]:
            vals=[r["article_over_femur"][a] for r in comparable]
            metrics.append({"leg":leg,"article":a,
                            "minimum_observed":round(min(vals),6),
                            "maximum_observed":round(max(vals),6),
                            "relative_span_of_observed_values":round(max(vals)/min(vals)-1,6),
                            "scope":"THREE_VOUCHER_COMPARISON_NOT_FAMILY_ACCEPTANCE_INTERVAL"})
    return metrics

def ball(scene,name,center,size):
    mesh=trimesh.creation.icosphere(subdivisions=1,radius=1)
    mesh.apply_scale(np.array(size,dtype=float)*.001)
    scene.add_geometry(mesh,geom_name=name,node_name=name,
        transform=trimesh.transformations.translation_matrix(np.array(center,dtype=float)*.001))

def make_reference_mesh(rec):
    scene=trimesh.Scene()
    car=rec["carapace"]
    ball(scene,"PROSOMA_CARAPACE_LENGTH_WIDTH_PUBLISHED_HEIGHT_UNKNOWN",
         (0,0,8),(car["width"]/2,car["length"]/2,3.5))
    ball(scene,"OPISTHOSOMA_UNMEASURED_PLACEHOLDER",
         (0,-.9*car["length"],8),(.42*car["width"],.55*car["length"],4.5))
    provenance=[]
    for side in (-1,1):
        side_tag="L" if side==-1 else "R"
        for ix,limb in enumerate(LEG_NUMERALS):
            distal=rec["legs"][limb] or {a:v for a,v in
                zip(ARTICLES,(.70*car["length"],.36*car["length"],.52*car["length"],
                              .54*car["length"],.35*car["length"]))}
            # Each side receives the same lengths, but this is not a measurement of bilateral equality.
            lengths={"coxa":.19*car["length"],"trochanter":.13*car["length"],**distal}
            root=(side*.37*car["width"],(.33-ix*.20)*car["length"],8)
            root_node=f"{side_tag}_{limb}_PROSOMA_ROOT_UNMEASURED"
            m=trimesh.creation.icosphere(subdivisions=0,radius=.0003)
            scene.add_geometry(m,geom_name=root_node,node_name=root_node,
                transform=trimesh.transformations.translation_matrix(np.array(root)*.001))
            parent=root_node
            parent_len=0
            for article in (*PROXIMAL,*ARTICLES):
                length=lengths[article]*.001
                mesh=trimesh.creation.cylinder(radius=.00042 if article in ("metatarsus","tarsus") else .00070,
                             segment=np.array([[0,0,0],[length,0,0]],dtype=float),sections=7)
                spin=(.05 if ix<2 else -.04)+(0.02 if side==1 else -.02)
                rot=trimesh.transformations.rotation_matrix(side*spin,[0,0,1])
                transform=trimesh.transformations.translation_matrix((parent_len,0,0))@rot
                node=f"{side_tag}_{limb}_{article.upper()}"
                scene.add_geometry(mesh,geom_name=node,node_name=node,
                                   parent_node_name=parent,transform=transform)
                measured_side=((side_tag=="L" and rec["measurement_side"]=="LEFT")
                               or (side_tag=="L" and rec["measurement_side"]=="PUBLICATION_NOT_EXPLICITLY_RECORDED"))
                status=("SOURCE_PUBLISHED_DISTAL_LENGTH_SIDE_UNCONFIRMED" if
                         measured_side and rec["measurement_side"]=="PUBLICATION_NOT_EXPLICITLY_RECORDED" and article in ARTICLES
                         else "PUBLISHED_LEFT_DISTAL_LENGTH" if measured_side and article in ARTICLES
                         else "MODELLED_BILATERAL_COPY_UNMEASURED" if article in ARTICLES and rec["legs"][limb] is not None
                         else "ENGINEERING_LENGTH_PLACEHOLDER")
                provenance.append({"segment":node,"length_mm":round(lengths[article],6),
                                   "evidence":status})
                parent=node
                parent_len=length
    for tag,x in (("L",-1),("R",1)):
        ball(scene,f"{tag}_FEMALE_PEDIPALP_PROXY",
             (x*.19*car["width"],.62*car["length"],7),
             (1.,3.,1.))
    scene.metadata={"source_specimen":rec["id"],"taxon":rec["name"],
                    "role":"NOT_APPROVED_RESEARCH_CALIBRATION_GEOMETRY",
                    "pose_faithful_to_source":False,"skinned_or_animated":False}
    return scene,provenance

def execute(source_path,out):
    data=load(source_path)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rows=normalized(data["exemplars"])
    spans=compare_ratio_span(rows)
    models=[]
    for rec in data["exemplars"]:
        scene,segments=make_reference_mesh(rec)
        raw=scene.export(file_type="glb")
        loaded=trimesh.load(io.BytesIO(raw),file_type="glb",force="scene")
        required={f"{s}_{l}_{a.upper()}" for s in ("L","R")
                  for l in LEG_NUMERALS for a in (*PROXIMAL,*ARTICLES)}
        if not required.issubset(loaded.graph.nodes):
            raise RuntimeError("EXPORTED_GLTF_DROPPED_NAMED_SEGMENTS")
        filename=f"{rec['id']}_EVIDENCE_ANCHORED_GEOMETRY_UNAPPROVED.glb"
        (out/filename).write_bytes(raw)
        measured=sum(1 for x in segments if x["evidence"].startswith("PUBLISHED_LEFT"))
        side_unconfirmed=sum(1 for x in segments if x["evidence"]=="SOURCE_PUBLISHED_DISTAL_LENGTH_SIDE_UNCONFIRMED")
        models.append({"specimen_id":rec["id"],"taxon":rec["name"],"filename":filename,
                       "sha256":hashlib.sha256(raw).hexdigest(),"named_segments":len(required),
                       "source_measured_left_segments":measured,
                       "published_side_not_specified_segments":side_unconfirmed,
                       "biology_approved":False,"natural_rest_pose_verified":False,
                       "real_camera_views_rendered":0})
    report={"schema":"VNMV1_THERAPHOSIDAE_THREE_EXEMPLAR_CONTRAST_REPORT_V1",
            "references":data["scientific_evidence"],"exemplars":len(data["exemplars"]),
            "different_genera":len({e["name"].split()[0] for e in data["exemplars"]}),
            "species_sex_profiles_scientifically_approved":0,
            "source_bounded_distal_article_records":sum(len(r["legs"][l]) for r in data["exemplars"]
                                                       for l in LEG_NUMERALS if r["legs"][l] is not None),
            "published_measurement_rows":rows,"observed_relative_length_spans":spans,
            "model_outputs":models,
            "male_and_juvenile_unknowns":data["additional_evidence_holds"],
            "family_wide_acceptable_ratio_ranges_inferred":False,
            "no_apply_to_card0016":True,
            "comment":"Three published specimens show variable limb proportions; topology is shared but actual family morphology and natural 3D angles remain unverified."}
    (out/"evidence_comparison_and_holds.json").write_text(json.dumps(report,indent=2))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",default="research/data/theraphosidae_three_females_comparison_v1.json")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    result=execute(a.source,a.out)
    print(json.dumps({k:v for k,v in result.items() if k not in ("published_measurement_rows","observed_relative_length_spans")},indent=2))
