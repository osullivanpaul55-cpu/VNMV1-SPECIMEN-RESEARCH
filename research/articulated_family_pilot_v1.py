#!/usr/bin/env python3
"""Stage-2 research: family-grouped, articulated neutral spider rigs.

Every geometry value is an artist-set structural placeholder, NOT a measured
species/family trait. Rigs are hierarchy-poseable but NOT skinned or animated.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
import trimesh

SEGMENTS=("coxa","trochanter","femur","patella","tibia","metatarsus","tarsus")
LEG_NUMERALS=("I","II","III","IV")
CAMERAS=("FRONTAL","WALKING_AWAY_REAR_OBLIQUE","LATERAL_PROFILE",
         "OBLIQUE_THREE_QUARTER","DORSAL_TOP_DOWN","POSTERIOR")


def key(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def eligible(row):
    e=row.get("source_evidence") or {}
    return (e.get("status")=="ACCEPTED" and e.get("matchType")=="EXACT"
            and e.get("rank")=="SPECIES"
            and e.get("canonicalName","").casefold()==row.get("queried_public_taxon_name","").casefold()
            and e.get("order")=="Araneae" and bool(e.get("family")))


def add_ellipsoid(scene, name, center, dims, parent="world"):
    m=trimesh.creation.icosphere(subdivisions=1)
    m.apply_scale(dims)
    scene.add_geometry(m,geom_name=name,node_name=name,parent_node_name=parent,
                       transform=trimesh.transformations.translation_matrix(center))


def build_graph():
    """Topology demonstration with rotation pivots at each exoskeletal joint."""
    scene=trimesh.Scene()
    add_ellipsoid(scene,"PROSOMA_UNMEASURED",(0,.25,.80),(.49,.55,.27))
    add_ellipsoid(scene,"OPISTHOSOMA_UNMEASURED",(0,-.75,.78),(.55,.62,.37))
    for sign in (-1,1):
        side="L" if sign==-1 else "R"
        for i,roman in enumerate(LEG_NUMERALS):
            ident=f"{side}_{roman}"
            root=(sign*.30,.59-i*.24,.78)
            add_ellipsoid(scene,f"{ident}_COXA_ATTACHMENT",root,(0.028,.028,.028))
            parent=f"{ident}_COXA_ATTACHMENT"
            prev=(0.,0.,0.)
            # Geometrical pose guides, not calibrated joint lengths or angles.
            directions=((.09,.02,-.015),(.10,.015,.018),(.33,.11,.13),
                        (.10,.06,-.01),(.30,.09,-.19),(.29,.10,-.24),
                        (.19,.055,-.31))
            for j,seg in enumerate(SEGMENTS):
                v=np.array((sign*directions[j][0],
                            (1.5-i)*directions[j][1],directions[j][2]),dtype=float)
                length=float(np.linalg.norm(v))
                assert length>.01
                radius=(.042 if j<4 else .026)
                m=trimesh.creation.cylinder(radius=radius,segment=np.array([[0.,0.,0.],v]),sections=7)
                node=f"{ident}_{seg.upper()}"
                scene.add_geometry(m,geom_name=node,node_name=node,parent_node_name=parent,
                                   transform=trimesh.transformations.translation_matrix(prev))
                parent=node
                prev=v
        # Two pedipalps are separate from the eight walking legs.
        add_ellipsoid(scene,f"{side}_PALP_ROOT_UNMEASURED",(sign*.22,.73,.71),(.055,.055,.05))
    scene.metadata={"role":"ARTICULATED_RIGID_JOINT_HIERARCHY_DEMO",
                    "biological_morphometry":"NONE",
                    "skin_weights":False,"animations":False}
    return scene


def run(source,out,shard,shards=5):
    if not (isinstance(shard,int) and 0<=shard<shards):
        raise ValueError("invalid shard")
    d=json.loads(Path(source).read_text(encoding="utf-8"))
    group=defaultdict(list)
    held=[]
    for row in d["records"]:
        e=row.get("source_evidence") or {}
        if eligible(row):
            group[e["family"]].append(row)
        else:
            held.append(row)
    # Deterministic assignment: one family rig is never built by two workers.
    families=sorted(group)
    targets=[f for i,f in enumerate(families) if i%shards==shard]
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    plans=[];num_species=0
    for f in targets:
        rows=sorted(group[f],key=lambda r:r["queried_public_taxon_name"].casefold())
        scene=build_graph()
        names=set(scene.graph.nodes)
        for side in ("L","R"):
            for roman in LEG_NUMERALS:
                for seg in SEGMENTS:
                    assert f"{side}_{roman}_{seg.upper()}" in names
        basename=f"generic_araneae_family_{key(f)}.glb"
        binary=scene.export(file_type="glb")
        (out/basename).write_bytes(binary)
        num_species+=len(rows)
        plans.append({
            "family_public_label":f,"template_lineage":"UNMEASURED_ARANEAE_ORDER_PLACEHOLDER",
            "glb":basename,"sha256":hashlib.sha256(binary).hexdigest(),
            "named_leg_segments":56,"walking_legs":8,"separate_palp_roots":2,
            "hierarchical_joint_pivots":True,"skinned_mesh":False,"animation_clips":0,
            "species_morphology_verified":False,"family_morphology_verified":False,
            "source_photo_bytes_used":False,"anatomy_approved":False,
            "species_candidates":[{
                "public_taxon_name":r["queried_public_taxon_name"],
                "name_match_source":r.get("source_url"),
                "species_measurement_status":"REQUIRES_INDEPENDENT_SOURCE_EVIDENCE",
                "sex_stage":"UNRESOLVED_FOR_RIG",
                "individual_original_photo_approved":False,
                "rig_status":"SHARED_FAMILY_RESEARCH_SCAFFOLD_NOT_SPECIES_RIG"
            } for r in rows],
            "needed_before_species_mesh":[
                "verify accepted taxon and original card identity privately",
                "independently review multiple genuine species reference angles",
                "research sex/life-stage morphology and joint/limb proportions",
                "fit body geometry, appendages and rest pose against source images",
                "source-bound 3D segmentation and occlusion uncertainty",
                "validate frontal, posterior, lateral and dorsal projections",
                "articulation limits, contact and collision review",
                "build texture and setae only after anatomy approval",
                "independent anatomical QA plus human approval"
            ],
            "camera_research_queue":list(CAMERAS)
        })
    report={
        "schema":"VNMV1_PUBLIC_ARTICULATED_FAMILY_PILOT_V1",
        "shard":shard,"shards":shards,"total_distinct_accepted_spider_families":len(families),
        "processed_families":len(plans),"adaptation_research_taxa":num_species,
        "held_public_name_records_in_source":len(held),
        "certified_species_rigs":0,"scientific_masters_approved":0,
        "purpose":"SHARED_RIGID_NODE_HIERARCHY_AND_RESEARCH_QUEUE_ONLY",
        "no_private_card_ids":True,"families":plans
    }
    (out/"manifest.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",default="data/roster_taxon_identity_evidence.json")
    p.add_argument("--shard",type=int,required=True)
    p.add_argument("--shards",type=int,default=5)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    result=run(args.source,args.out,args.shard,args.shards)
    print(json.dumps({k:v for k,v in result.items() if k!="families"}))
