#!/usr/bin/env python3
"""Five-shard public-safe species photo research. NO animal or licence approval.
No private card IDs/specimens, no credentials, no image generation; bounded iNaturalist requests.
"""
from __future__ import annotations
import argparse, hashlib, io, json, re, time
from pathlib import Path
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
from PIL import Image, UnidentifiedImageError
from pose_reference import unverified_text_pose_hints, research_needs

SHARDS=5; MAX_IMAGE_BYTES=5_000_000; ALLOWED={'cc0','cc-by'}
HOSTS={'static.inaturalist.org','inaturalist-open-data.s3.amazonaws.com','inaturalist-open-data.s3.us-west-2.amazonaws.com'}
API='https://api.inaturalist.org/v1/observations'
UA='VNMV1-SPECIMEN-RESEARCH/1.0 (open CC metadata research; public provenance and attribution)'

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def choose_species(seed:dict, shard:int,cycle:int,per_worker:int,previous:dict)->list[dict]:
    species=seed['species']
    if seed.get('schema')!='VNMV1_PUBLIC_RESEARCH_SPECIES_SEED_V1' or len(species)!=len({v['key'] for v in species}):raise ValueError('INVALID_SPECIES_SEED')
    if not 0<=shard<SHARDS or cycle<0 or not 1<=per_worker<=6: raise ValueError('BAD_CYCLE_OR_SHARD')
    # deterministic disjoint workers for the initial full sweep, then
    # revisit low-count taxa without inserting fictitious filler photographs.
    n=len(species);start=(cycle*SHARDS*per_worker+shard*per_worker)%n
    out=[species[(start+i)%n] for i in range(per_worker)]
    # No duplicate assignment between workers within a normal sweep; at the
    # wrap boundary the second pass reuses the first handful intentionally.
    return out

def fetch(url:str,cap:int,timeout:int=12)->bytes:
    req=Request(url,headers={'User-Agent':UA,'Accept':'application/json,image/*'})
    for attempt in range(3):
        try:
            with urlopen(req,timeout=timeout) as r:
                if r.status!=200:raise ValueError(f'HTTP_{r.status}')
                b=r.read(cap+1)
                if len(b)>cap:raise ValueError('RESPONSE_TOO_LARGE')
                return b
        except Exception as exc:
            if attempt==2: raise
            time.sleep(.4*(attempt+1))
    raise RuntimeError('UNREACHABLE')

def image_url(url:str)->str|None:
    if not isinstance(url,str):return None
    p=urlparse(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or not p.path.startswith('/photos/') or p.query:return None
    if not re.search(r'/(?:square|thumb|small|medium|large|original)\.(?:jpe?g|png)$',p.path,re.I):return None
    return urlunparse((p.scheme,p.netloc,re.sub(r'/(?:square|thumb|small|large|original)\.', '/medium.',p.path),'','',''))

def inspect_image(b:bytes)->tuple[str,int,int,int]:
    try:
        with Image.open(io.BytesIO(b)) as x:x.verify()
        with Image.open(io.BytesIO(b)) as x:
            if x.format not in ('JPEG','PNG','WEBP') or min(x.size)<180 or x.width*x.height>40_000_000:
                raise ValueError('UNSUPPORTED_IMAGE_OR_DIMENSIONS')
            fmt=x.format;w,h=x.size
            gray=x.convert('L').resize((9,8),Image.Resampling.LANCZOS)
            pixels=list(gray.get_flattened_data() if hasattr(gray,'get_flattened_data') else gray.getdata())
            ph=0
            for y in range(8):
                for xx in range(8):ph=(ph<<1)|int(pixels[y*9+xx]>pixels[y*9+xx+1])
            return {'JPEG':'jpg','PNG':'png','WEBP':'webp'}[fmt],w,h,ph
    except (OSError,ValueError,UnidentifiedImageError) as exc:
        raise ValueError('PHOTO_DECODE_OR_DIMENSIONS_FAILED') from exc

def discover(taxon:str,seen:set[str],api_fetch=fetch,pages:int=8,per_page:int=25)->list[dict]:
    results=[];checked=set()
    for page in range(1,pages+1):
        qs=urlencode({'taxon_name':taxon,'quality_grade':'research','photos':'true','photo_license':'cc0,cc-by','per_page':per_page,'page':page})
        payload=json.loads(api_fetch(API+'?'+qs,3_000_000))
        obs=payload.get('results',[])
        if not isinstance(obs,list):raise ValueError('INVALID_OBSERVATION_RESPONSE')
        for ob in obs:
            t=ob.get('taxon') or {}
            if t.get('name')!=taxon or t.get('rank')!='species' or ob.get('quality_grade')!='research':continue
            oid=ob.get('id')
            if not isinstance(oid,int):continue
            for p in ob.get('photos',[]):
                lic=(p.get('license_code') or '').lower();pid=p.get('id'); url=image_url(p.get('url'))
                if lic not in ALLOWED or not isinstance(pid,int) or not url:continue
                key=f'inat:{pid}'
                if key in seen or key in checked:continue
                checked.add(key)
                results.append({'photo_key':key,'observation_id':oid,'photo_id':pid,'taxon':taxon,
                  'license_code':lic,'license_url':p.get('license_url'),
                  'license_version':'UNVERIFIED_SOURCE_CHECK_REQUIRED',
                  'attribution':p.get('attribution') or (ob.get('user') or {}).get('login') or 'UNKNOWN',
                  'source_url':f'https://www.inaturalist.org/observations/{oid}',
                  'thumbnail_url':url,'sex':'UNKNOWN_UNVERIFIED',
                  'taxon_authority':'COMMUNITY_RESEARCH_GRADE_NOT_USER_APPROVED',
                  'rights_verdict':'CANDIDATE_METADATA_ONLY_NOT_GENERATION_CLEARED',
                  'review_state':'PENDING',
                  'pose_id':'UNREVIEWED','pose_review_status':'VISUAL_REVIEW_REQUIRED',
                  'unverified_observer_text_pose_hints':unverified_text_pose_hints(ob.get('description') or '')})
        if len(obs)<per_page:break
        time.sleep(.12)
    return results

def research_species(spec:dict,previous:dict,out:Path,max_per_species:int=12,discovery=discover,download=fetch)->dict:
    taxon=spec['name'];key=spec['key'];old=(previous.get('species') or {}).get(key,{})
    prior=old.get('candidates',[]);seen={v.get('photo_key') for v in prior}
    accepted=[];rejections=[];phashes=[];obs_counts={}
    # Every return is candidate-only; never auto-promote species, sex or licence.
    try: found=discovery(taxon,seen)
    except Exception as exc:
        return {'key':key,'taxon':taxon,'status':'RETRY_DISCOVERY','new_candidates':[], 'rejections':[str(exc)[:140]]}
    for c in found:
        if len(accepted)>=max_per_species:break
        # Multiple independent frames from one observation may show different angles.
        # Allow up to three, but do not mistake them for three specimens.
        if obs_counts.get(c['observation_id'],0)>=3:continue
        try:
            data=download(c['thumbnail_url'],MAX_IMAGE_BYTES)
            ext,w,h,dh=inspect_image(data);digest=sha(data)
            if any(p.get('sha256')==digest or ((dh^p['phash']).bit_count()<=5) for p in phashes):
                rejections.append({'key':c['photo_key'],'reason':'SAME_OR_NEAR_DUPLICATE_IMAGE'});continue
            name=f"media/{key}/{c['photo_id']}.{ext}";dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
            accepted.append({**c,'sha256':digest,'bytes':len(data),'width':w,'height':h,
                'archive_member':name,'photo_identity':'UNVERIFIED','sex':'UNKNOWN_UNVERIFIED',
                'independent_photo_status':'DISTINCT_FRAME_PROVISIONAL_HASH_FILTER',
                'same_observation_reference_group':c['observation_id'],
                'pose_id':'UNREVIEWED','pose_review_status':'VISUAL_REVIEW_REQUIRED',
                'approved_for_imagegen':False})
            obs_counts[c['observation_id']]=obs_counts.get(c['observation_id'],0)+1;phashes.append({'sha256':digest,'phash':dh})
        except Exception as exc:
            rejections.append({'key':c.get('photo_key'),'reason':str(exc)[:140]})
    return {'key':key,'taxon':taxon,'status':'REVIEW_REQUIRED' if accepted else ('ALREADY_COLLECTED_OR_NO_NEW_LEADS' if prior else 'NO_CANDIDATES'),
            'new_candidates':accepted,'rejections':rejections[:20],
            'camera_view_research_needs':research_needs()}

def run(seed:dict,index:dict,shard:int,cycle:int,per_worker:int,limit:int,out:Path,**kwargs)->dict:
    specs=choose_species(seed,shard,cycle,per_worker,index)
    out.mkdir(parents=True,exist_ok=True);rows=[]
    for spec in specs:
        row=research_species(spec,index,out,limit,**kwargs);rows.append(row)
        print(spec['name'], row['status'],len(row['new_candidates']),flush=True)
    report={'schema':'VNMV1_PUBLIC_PHOTO_RESEARCH_SHARD_V1','shard':shard,'cycle':cycle,'species_processed':len(rows),
            'camera_view_research_standard':research_needs(),
            'downloaded_candidates':sum(len(r['new_candidates']) for r in rows),'approvals':0,'imagegen_invocations':0,'species':rows}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--seed',type=Path,required=True);p.add_argument('--index',type=Path,required=True)
    p.add_argument('--shard',type=int,required=True);p.add_argument('--cycle',type=int,required=True)
    p.add_argument('--species-per-worker',type=int,default=4);p.add_argument('--max-photos',type=int,default=12)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if not 1<=a.max_photos<=18:raise SystemExit('Bad photo limit')
    run(json.loads(a.seed.read_text()),json.loads(a.index.read_text()),a.shard,a.cycle,a.species_per_worker,a.max_photos,a.out)
if __name__=='__main__':main()