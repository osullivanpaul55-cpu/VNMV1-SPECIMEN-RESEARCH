#!/usr/bin/env python3
"""Five-shard PUBLIC-name-only neutral anatomical 3D blockout research.

NOT species morphometry, sex determination, photogrammetry, or an approved rig.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

SUPPORTED = {
    'Araneae': 'SPIDER_8',
    'Scorpiones': 'SCORPION_8',
    'Mantodea': 'INSECT_6',
    'Coleoptera': 'INSECT_6',
    'Lepidoptera': 'INSECT_6',
    'Odonata': 'INSECT_6',
    'Hemiptera': 'INSECT_6',
    'Phasmida': 'INSECT_6',
    'Amblypygi': 'AMBLYPYGI_8',
}
LEG_SPIDER = ['coxa', 'trochanter', 'femur', 'patella', 'tibia', 'metatarsus', 'tarsus']
LEG_INSECT = ['coxa', 'trochanter', 'femur', 'tibia', 'tarsus']


def ball(scene, name, p, scale):
    mesh = trimesh.creation.icosphere(subdivisions=1, radius=1.0)
    mesh.apply_scale(scale)
    mesh.apply_translation(p)
    scene.add_geometry(mesh, geom_name=name)


def segment(scene, name, a, b, radius):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    if np.linalg.norm(b-a) < 0.005:
        raise ValueError('degenerate segment '+name)
    mesh = trimesh.creation.cylinder(radius=radius, segment=np.vstack((a,b)), sections=7)
    scene.add_geometry(mesh, geom_name=name)


def build_generic(order):
    """Order-level topology blockout, not a taxon-specific model."""
    plan = SUPPORTED[order]
    scene = trimesh.Scene()
    limbs = []
    if plan in ('SPIDER_8', 'AMBLYPYGI_8', 'SCORPION_8'):
        ball(scene, 'prosoma', [0, 0.15, 0.82], [0.53, 0.55, 0.27])
        ball(scene, 'opisthosoma', [0, -0.92, 0.83], [0.65, 0.72, 0.42])
        for side in (-1, 1):
            for ix in range(4):
                y = 0.55-0.30*ix
                x = side*(0.36+0.02*ix)
                reach = 0.76+(ix*0.045)
                rear = (ix-1.4)*0.5
                points = [(x,y,0.77), (x+side*.11,y+rear*.12,.74),
                          (x+side*.19,y+rear*.23,.73),
                          (x+side*(reach*.72),y+rear*.85,1.02),
                          (x+side*(reach*.91),y+rear*1.09,.98),
                          (x+side*(reach*1.22),y+rear*1.22,.56),
                          (x+side*(reach*1.43),y+rear*1.35,.24),
                          (x+side*(reach*1.51),y+rear*1.40,.085)]
                if plan == 'AMBLYPYGI_8' and ix == 0:
                    points[-2] = (x+side*2.1, y+0.65,.64)
                    points[-1] = (x+side*2.6, y+0.8,.47)
                names = LEG_SPIDER if plan != 'SCORPION_8' else [*LEG_SPIDER[:-2], 'basitarsus', 'telotarsus']
                legid = ('L' if side < 0 else 'R')+str(ix+1)
                for j,n in enumerate(names):
                    segment(scene, f'{legid}_{n}', points[j], points[j+1], .035 if j>4 else .055)
                    ball(scene, f'{legid}_joint{j+1}', points[j+1], [.056]*3)
                limbs.append({'limb':legid, 'segments':names, 'joints_xyz':points,
                              'measurement_status':'UNMEASURED_GENERIC_ORDER_GEOMETRY'})
        for s in (-1, 1):
            segment(scene, f'pedipalp_{s}', (s*.23,.52,.76), (s*.28,.96,.46), .065)
        if plan == 'SCORPION_8':
            prev = (0,-1.5,.93)
            for i in range(5):
                nextp = (0,-1.8-i*.24, .98+i*.23)
                segment(scene, f'metasoma_provisional_{i+1}', prev, nextp, .13)
                prev = nextp
    else:
        ball(scene,'thorax',[0,0,.7],[.24,.43,.28])
        ball(scene,'abdomen',[0,-.86,.67],[.33,.69,.3])
        ball(scene,'head',[0,.55,.76],[.28,.25,.27])
        for side in (-1,1):
            for ix in range(3):
                y=.35-.36*ix
                x=side*.17
                points=[(x,y,.68),(x+side*.13,y+.02,.62),
                        (x+side*.23,y+.03,.6),(x+side*.62,y+(ix-1)*.30,.84),
                        (x+side*.82,y+(ix-1)*.40,.32),
                        (x+side*.92,y+(ix-1)*.42,.04)]
                legid=('L' if side<0 else 'R')+str(ix+1)
                for j,n in enumerate(LEG_INSECT):
                    segment(scene,f'{legid}_{n}',points[j],points[j+1],.038)
                limbs.append({'limb':legid,'segments':LEG_INSECT,'joints_xyz':points,
                              'measurement_status':'UNMEASURED_GENERIC_ORDER_GEOMETRY'})
        # No wings: insect orders differ by family, sex and life stage.
    scene.metadata={'geometry_role':'UNAPPROVED_ORDER_LEVEL_NEUTRAL_BLOCKOUT'}
    return scene, limbs, plan


def valid_taxon(row):
    ev=row.get('source_evidence') or {}
    if ev.get('rank')!='SPECIES' or ev.get('matchType')!='EXACT' or ev.get('status')!='ACCEPTED':
        return 'HOLD_NAME_NOT_EXACT_ACCEPTED_SPECIES'
    if ev.get('canonicalName','').casefold()!=row.get('queried_public_taxon_name','').casefold():
        return 'HOLD_NAME_MISMATCH'
    if ev.get('order') not in SUPPORTED:
        return 'HOLD_BODY_PLAN_NOT_IMPLEMENTED'
    return None


def run(source, outdir, shard, shards=5):
    if not 0 <= shard < shards:
        raise ValueError('shard must be in 0..shards-1')
    data=json.loads(Path(source).read_text(encoding='utf-8'))
    rows=sorted(data['records'],key=lambda r:r['queried_public_taxon_name'].casefold())
    outdir=Path(outdir)
    outdir.mkdir(parents=True,exist_ok=True)
    records=[]
    for ix,row in enumerate(rows):
        if ix%shards!=shard:
            continue
        name=row['queried_public_taxon_name']
        ev=row.get('source_evidence') or {}
        reason=valid_taxon(row)
        record={'taxon_name_public_lead':name, 'source_url':row.get('source_url'),
                'order':ev.get('order'),'family':ev.get('family'),
                'sex':'UNKNOWN','approved_3d_mesh':False,'approved_scientific_anatomy':False,
                'poseable_skeletal_rig':False,'original_private_card_photo_used':False,
                'model_input_sources':'PUBLIC_TAXON_NAME_MATCH_ONLY',
                'status':reason or 'GENERIC_BLOCKOUT_ONLY__REQUIRES_SPECIES_EVIDENCE'}
        if not reason:
            scene,limbs,plan=build_generic(ev['order'])
            key=hashlib.sha256(name.encode()).hexdigest()[:16]
            p=outdir/f'blockout_{key}.glb'
            p.write_bytes(scene.export(file_type='glb'))
            record.update({'archetype':plan,'glb':p.name,
                           'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                           'leg_chain_count':len(limbs),
                           'limb_names':[x['limb'] for x in limbs],
                           'joint_data_role':'PROCEDURAL_GEOMETRY_NOT_OBSERVED_MORPHOMETRY'})
        records.append(record)
    manifest={'schema':'VNMV1_PUBLIC_ANATOMY_BLOCKOUT_SHARD_V1','shard':shard,
              'shards':shards,'research_rows':len(records),
              'generic_blockouts':sum('glb' in r for r in records),
              'species_anatomy_approved':0,'poseable_species_rigs_approved':0,
              'do_not_import_as_master':True,'records':records}
    (outdir/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',default='data/roster_taxon_identity_evidence.json')
    p.add_argument('--out',required=True)
    p.add_argument('--shard',type=int,required=True)
    p.add_argument('--shards',type=int,default=5)
    a=p.parse_args()
    m=run(a.source,a.out,a.shard,a.shards)
    print(json.dumps({k:v for k,v in m.items() if k!='records'}))
