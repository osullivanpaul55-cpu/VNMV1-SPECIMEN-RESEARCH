#!/usr/bin/env python3
"""Five-shard public-safe species photo research. NO animal or licence approval.
No private card IDs/specimens, no credentials, no image generation; bounded iNaturalist and Commons requests.
"""
from __future__ import annotations
import argparse, hashlib, io, json, re, time
from html import unescape
from pathlib import Path
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
from PIL import Image, UnidentifiedImageError
from pose_reference import unverified_text_pose_hints, unverified_text_behaviour_hints, research_needs

SHARDS=5; MAX_IMAGE_BYTES=5_000_000; ALLOWED={'cc0','cc-by'}; MAX_LINK_LEADS_PER_SPECIES_PER_CYCLE=30
HOSTS={'static.inaturalist.org','inaturalist-open-data.s3.amazonaws.com','inaturalist-open-data.s3.us-west-2.amazonaws.com'}
API='https://api.inaturalist.org/v1/observations'
COMMONS_API='https://commons.wikimedia.org/w/api.php'
GBIF_API='https://api.gbif.org/v1/occurrence/search'
UA='VNMV1-SPECIMEN-RESEARCH/1.0 (open CC metadata research; public provenance and attribution)'

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def merge_seed_with_extension(seed:dict, extension:dict)->dict:
    """Merge exact accepted taxa into a deterministic block for the next research cycles."""
    if seed.get('schema')!='VNMV1_PUBLIC_RESEARCH_SPECIES_SEED_V1':
        raise ValueError('INVALID_SPECIES_SEED')
    if extension.get('schema')!='VNMV1_PUBLIC_RESEARCH_REFERENCE_EXTENSION_V1':
        raise ValueError('INVALID_REFERENCE_EXTENSION')
    base=list(seed.get('species') or [])
    by_name={str(x.get('name','')).strip().casefold():x for x in base}
    extension_rows=[]
    extension_names=set()
    for row in extension.get('species') or []:
        if not isinstance(row,dict):
            raise ValueError('INVALID_EXTENSION_SPECIES')
        name=str(row.get('name','')).strip()
        rank=str(row.get('rank','')).upper()
        key=str(row.get('key','')).strip()
        if not name or not key or rank not in {'SPECIES','SUBSPECIES'}:
            raise ValueError('EXTENSION_REQUIRES_EXACT_ACCEPTED_TAXA')
        normalized=name.casefold()
        if normalized in extension_names:
            raise ValueError('DUPLICATE_EXTENSION_TAXON')
        extension_names.add(normalized)
        merged=dict(by_name.get(normalized) or {})
        merged.update(row)
        merged['name']=name
        merged['key']=by_name.get(normalized,{}).get('key',key)
        merged['taxon_status']='RESEARCH_CANDIDATE_UNVERIFIED'
        extension_rows.append(merged)
    remaining=[row for row in base if str(row.get('name','')).strip().casefold() not in extension_names]
    position=extension.get('insert_extension_species_at',len(remaining))
    if not isinstance(position,int) or position<0:
        raise ValueError('INVALID_EXTENSION_INSERT_POSITION')
    position=min(position,len(remaining))
    combined=remaining[:position]+extension_rows+remaining[position:]
    if len(combined)!=len({row.get('key') for row in combined}):
        raise ValueError('DUPLICATE_MERGED_TAXON_KEY')
    return {**seed,'unique_research_taxa':len(combined),'species':combined}

def choose_species(seed:dict, shard:int,cycle:int,per_worker:int,previous:dict)->list[dict]:
    species=seed['species']
    if seed.get('schema')!='VNMV1_PUBLIC_RESEARCH_SPECIES_SEED_V1' or len(species)!=len({v['key'] for v in species}):raise ValueError('INVALID_SPECIES_SEED')
    if not 0<=shard<SHARDS or cycle<0 or not 1<=per_worker<=12: raise ValueError('BAD_CYCLE_OR_SHARD')
    n=len(species);per_cycle=SHARDS*per_worker
    # Preserve a deterministic, disjoint first sweep across the full catalog.
    # Do not wrap the final partial batch: wrapping skips the last taxa and
    # duplicates the first ones when n is not divisible by per_cycle.
    full_sweep_cycles=(n+per_cycle-1)//per_cycle
    if cycle<full_sweep_cycles:
        start=cycle*per_cycle+shard*per_worker
        return species[start:min(start+per_worker,n)]
    indexed=(previous.get('species') or {}) if isinstance(previous,dict) else {}
    ranked=[]
    for position,spec in enumerate(species):
        prior=indexed.get(spec['key'],{})
        if not isinstance(prior,dict):prior={}
        seen={str(x.get('photo_key')) for x in
              list(prior.get('candidates') or [])+list(prior.get('link_only_leads') or [])
              if isinstance(x,dict) and x.get('photo_key')}
        count=len(seen)
        if count<9:band,gap=0,9-count
        elif count<12:band,gap=1,12-count
        elif count<15:band,gap=2,15-count
        else:band,gap=3,0
        raw_last=prior.get('last_cycle',-1)
        try:last_cycle=int(raw_last)
        except (TypeError,ValueError):last_cycle=-1
        # Within each coverage band, fill the largest shortfall first, then
        # retry the taxa least recently visited. Stable catalog order breaks ties.
        ranked.append((band,-gap,last_cycle,position,spec))
    ranked.sort(key=lambda row:row[:4])
    start=shard*per_worker
    return [row[4] for row in ranked[start:start+per_worker]]

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
    return urlunparse((p.scheme,p.netloc,re.sub(r'/(?:square|thumb|small|large|original)\.', '/large.',p.path),'','',''))

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
    """Collect exact species-level community observations at every quality grade.

    Research Grade is useful context, not expert verification. Needs ID and
    Casual records remain photo-review leads when the displayed community taxon
    matches exactly; each grade is preserved for the human reviewer.
    """
    results=[];checked=set()
    for page in range(1,pages+1):
        qs=urlencode({'taxon_name':taxon,'photos':'true','per_page':per_page,'page':page})
        payload=json.loads(api_fetch(API+'?'+qs,3_000_000))
        obs=payload.get('results',[])
        if not isinstance(obs,list):raise ValueError('INVALID_OBSERVATION_RESPONSE')
        for ob in obs:
            t=ob.get('taxon') or {}
            if t.get('name')!=taxon or t.get('rank')!='species':continue
            oid=ob.get('id')
            if not isinstance(oid,int):continue
            grade=str(ob.get('quality_grade') or 'UNKNOWN').lower()
            if grade=='research':
                authority='COMMUNITY_RESEARCH_GRADE_NOT_USER_APPROVED'
            elif grade in {'needs_id','casual'}:
                authority=f'COMMUNITY_{grade.upper()}_NOT_USER_APPROVED'
            else:
                authority='COMMUNITY_STATUS_UNVERIFIED_NOT_USER_APPROVED'
            for p in ob.get('photos',[]):
                lic=(p.get('license_code') or '').lower();pid=p.get('id'); url=image_url(p.get('url'))
                if not isinstance(pid,int):continue
                allowed=lic in ALLOWED and url is not None
                key=f'inat:{pid}'
                if key in seen or key in checked:continue
                checked.add(key)
                results.append({'photo_key':key,'observation_id':oid,'photo_id':pid,'taxon':taxon,
                  'observation_quality_grade':grade,'link_only':not allowed,
                  'redistribution_allowed_by_collector':allowed,
                  'license_code':lic or 'UNKNOWN','license_url':p.get('license_url'),
                  'license_research_status':'UNKNOWN_NO_LICENSE_METADATA' if not lic else ('CC0_OR_CC_BY_CANDIDATE' if allowed else 'NON_ARCHIVABLE_RIGHTS_NOT_CLEARED'),
                  'research_use_status':'USE_SOURCE_LINK_IMMEDIATELY_FOR_RESEARCH',
                  'license_version':'UNVERIFIED_SOURCE_CHECK_REQUIRED',
                  'attribution':p.get('attribution') or (ob.get('user') or {}).get('login') or 'UNKNOWN',
                  'source_url':f'https://www.inaturalist.org/observations/{oid}',
                  'review_preview_url':url,'thumbnail_url':url if allowed else None,'sex':'UNKNOWN_UNVERIFIED',
                  'taxon_authority':authority,
                  'rights_verdict':'CANDIDATE_METADATA_ONLY_NOT_GENERATION_CLEARED',
                  'review_state':'PENDING',
                  'pose_id':'UNREVIEWED','pose_review_status':'VISUAL_REVIEW_REQUIRED',
                  'unverified_observer_text_pose_hints':unverified_text_pose_hints(ob.get('description') or ''),
                  'unverified_observer_behaviour_hints':unverified_text_behaviour_hints(ob.get('description') or '')})
        if len(obs)<per_page:break
        time.sleep(.12)
    return results

def _commons_text(meta:dict,key:str)->str:
    value=meta.get(key,{})
    if isinstance(value,dict):value=value.get('value','')
    return unescape(re.sub(r'<[^>]*>',' ',str(value or ''))).replace('\\n',' ').strip()[:700]

def discover_commons(taxon:str,seen:set[str],api_fetch=fetch,limit:int=12)->list[dict]:
    """Find Commons file pages by text search, keeping every hit as an unverified source link."""
    if limit<=0:return []
    results=[];checked=set()
    taxon_tag=hashlib.sha256(taxon.casefold().encode('utf-8')).hexdigest()[:12]
    queries=[(f'"{taxon}"','EXACT_PHRASE'),(taxon,'UNQUOTED_TEXT')]
    for term,match_mode in queries:
        params={'action':'query','format':'json','formatversion':'2','generator':'search',
            'gsrsearch':term,'gsrnamespace':'6','gsrlimit':str(min(50,max(10,limit*2))),
            'prop':'imageinfo','iiprop':'url|extmetadata','iiurlwidth':'640',
            'iiextmetadatafilter':'Artist|Credit|LicenseShortName|LicenseUrl'}
        payload=json.loads(api_fetch(COMMONS_API+'?'+urlencode(params),3_000_000))
        pages=(payload.get('query') or {}).get('pages',[])
        if isinstance(pages,dict):pages=list(pages.values())
        if not isinstance(pages,list):raise ValueError('INVALID_COMMONS_SEARCH_RESPONSE')
        for page in pages:
            if not isinstance(page,dict) or page.get('ns')!=6:continue
            page_id=page.get('pageid')
            if not isinstance(page_id,int):continue
            infos=page.get('imageinfo') or []
            if not isinstance(infos,list) or not infos:continue
            info=infos[0] if isinstance(infos[0],dict) else {}
            source_url=info.get('descriptionurl')
            parsed=urlparse(source_url or '')
            if (parsed.scheme!='https' or parsed.hostname!='commons.wikimedia.org'
                or not parsed.path.startswith('/wiki/File:') or parsed.username or parsed.password
                or parsed.query or parsed.fragment):continue
            photo_key=f'commons:{taxon_tag}:{page_id}'
            if photo_key in seen or photo_key in checked:continue
            checked.add(photo_key)
            meta=info.get('extmetadata') or {}
            artist=_commons_text(meta,'Artist')
            credit=_commons_text(meta,'Credit')
            license_claim=_commons_text(meta,'LicenseShortName')
            license_url=_commons_text(meta,'LicenseUrl')
            warnings=['TEXT_SEARCH_MATCH_ONLY','PHOTO_IDENTITY_NOT_VISUALLY_REVIEWED',
                'LICENCE_AND_ATTRIBUTION_CLAIMS_REQUIRE_SOURCE_CHECK']
            if match_mode=='UNQUOTED_TEXT':
                warnings.append('UNQUOTED_TEXT_MATCH_REQUIRES_EXTRA_TAXON_CHECK')
            results.append({'photo_key':photo_key,'photo_id':page_id,'taxon':taxon,
                'source_title':str(page.get('title') or '')[:500],
                'source_url':source_url,'review_preview_url':info.get('thumburl') or info.get('url'),'source_type':'WIKIMEDIA_COMMONS_FILE_PAGE',
                'source_search_term':taxon,'source_search_query':term,'source_search_mode':match_mode,
                'taxon_match_status':'TEXT_SEARCH_MATCH_NOT_TAXONOMICALLY_VERIFIED',
                'taxon_authority':'WIKIMEDIA_TEXT_SEARCH_NOT_USER_APPROVED',
                'observation_quality_grade':None,'link_only':True,
                'redistribution_allowed_by_collector':False,
                'license_code':'UNKNOWN_PENDING_VERIFICATION',
                'license_url':license_url or None,
                'source_license_claim':license_claim or 'No licence claim returned by Commons API',
                'license_research_status':'COMMONS_METADATA_CLAIM_NOT_INDEPENDENTLY_VERIFIED',
                'research_use_status':'RESEARCH_LINK_AVAILABLE_NOW',
                'license_version':'UNVERIFIED_SOURCE_CHECK_REQUIRED',
                'attribution':artist or credit or 'Photographer or credit unconfirmed',
                'candidate_warning':warnings,
                'rights_verdict':'CANDIDATE_METADATA_ONLY_NOT_GENERATION_CLEARED',
                'review_state':'PENDING','pose_id':'UNREVIEWED',
                'pose_review_status':'VISUAL_REVIEW_REQUIRED','thumbnail_url':None,
                'media_copied_to_public_repo':False,'approved_for_imagegen':False,
                'reviewed_by_human':False})
            if len(results)>=limit:return results
    return results

def _normalized_taxon_text(value:str)->str:
    return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9]+',' ',str(value or '').casefold())).strip()

def discover_gbif(taxon:str,seen:set[str],api_fetch=fetch,limit:int=12)->list[dict]:
    """Find GBIF occurrence pages carrying still-image media; keep media link-only."""
    if limit<=0:return []
    params={'scientificName':taxon,'mediaType':'StillImage','limit':str(min(100,max(12,limit*3)))}
    payload=json.loads(api_fetch(GBIF_API+'?'+urlencode(params),3_000_000))
    rows=payload.get('results',[])
    if not isinstance(rows,list):raise ValueError('INVALID_GBIF_OCCURRENCE_RESPONSE')
    target=_normalized_taxon_text(taxon);target_words=target.split()
    if len(target_words)<2:return []
    core=' '.join(target_words[:2])
    tag=hashlib.sha256(taxon.casefold().encode('utf-8')).hexdigest()[:12]
    results=[];checked=set()
    for occurrence in rows:
        if not isinstance(occurrence,dict):continue
        rank=str(occurrence.get('taxonRank') or '').upper()
        if rank not in {'SPECIES','SUBSPECIES'}:continue
        names=[occurrence.get('scientificName'),occurrence.get('acceptedScientificName'),
               occurrence.get('verbatimScientificName')]
        normalized=[_normalized_taxon_text(name) for name in names if name]
        if not any(core in name for name in normalized):continue
        exact=any(name==target or name.startswith(target+' ') for name in normalized)
        occurrence_id=occurrence.get('key')
        if not isinstance(occurrence_id,(int,str)) or not str(occurrence_id).isdigit():continue
        media=occurrence.get('media') or []
        if not isinstance(media,list):continue
        for media_index,item in enumerate(media):
            if not isinstance(item,dict) or item.get('type') not in (None,'StillImage'):continue
            media_reference=str(item.get('references') or '')
            inat_photo=re.search(r'/photos/([0-9]+)(?:$|[/?#])',media_reference)
            if inat_photo and f'inat:{inat_photo.group(1)}' in seen:continue
            identity=str(item.get('identifier') or media_reference or
                item.get('title') or f'{occurrence_id}:{media_index}')
            media_tag=hashlib.sha256(identity.encode('utf-8')).hexdigest()[:12]
            photo_key=f'gbif:{tag}:{occurrence_id}:{media_tag}'
            if photo_key in seen or photo_key in checked:continue
            checked.add(photo_key)
            gbif_url=f'https://www.gbif.org/occurrence/{occurrence_id}'
            source_license=str(item.get('license') or occurrence.get('license') or '')
            creator=str(item.get('creator') or item.get('rightsHolder') or
                occurrence.get('rightsHolder') or occurrence.get('recordedBy') or
                'Photographer or rights holder unconfirmed')
            warnings=['GBIF_OCCURRENCE_NOT_USER_APPROVED','PHOTO_IDENTITY_NOT_VISUALLY_REVIEWED',
                'LICENCE_AND_ATTRIBUTION_CLAIMS_REQUIRE_SOURCE_CHECK']
            if not exact:warnings.append('SPECIES_NAME_VARIANT_REQUIRES_TAXON_REVIEW')
            results.append({'photo_key':photo_key,'photo_id':media_tag,'observation_id':str(occurrence_id),
                'taxon':taxon,'source_title':str(item.get('title') or occurrence.get('scientificName') or '')[:500],
                'source_url':gbif_url,'secondary_source_url':media_reference or None,
                'review_preview_url':item.get('identifier') or None,
                'source_type':'GBIF_OCCURRENCE_MEDIA_PAGE','source_search_term':taxon,
                'source_search_mode':'GBIF_SCIENTIFIC_NAME_WITH_STILL_IMAGE_FILTER',
                'source_taxon_name':str(occurrence.get('scientificName') or ''),
                'source_accepted_taxon_name':str(occurrence.get('acceptedScientificName') or ''),
                'taxon_match_status':'SPECIES_NAME_MATCH_NOT_USER_APPROVED' if exact else 'GENUS_SPECIES_NAME_VARIANT_REQUIRES_REVIEW',
                'taxon_authority':'GBIF_OCCURRENCE_NOT_USER_APPROVED',
                'observation_quality_grade':None,'link_only':True,
                'redistribution_allowed_by_collector':False,
                'license_code':'UNKNOWN_PENDING_VERIFICATION',
                'license_url':source_license or None,
                'source_license_claim':source_license or 'No licence claim returned in GBIF media metadata',
                'license_research_status':'GBIF_MEDIA_METADATA_CLAIM_NOT_INDEPENDENTLY_VERIFIED',
                'research_use_status':'RESEARCH_LINK_AVAILABLE_NOW',
                'license_version':'UNVERIFIED_SOURCE_CHECK_REQUIRED','attribution':creator,
                'candidate_warning':warnings,
                'rights_verdict':'CANDIDATE_METADATA_ONLY_NOT_GENERATION_CLEARED',
                'review_state':'PENDING','pose_id':'UNREVIEWED',
                'pose_review_status':'VISUAL_REVIEW_REQUIRED','thumbnail_url':None,
                'media_copied_to_public_repo':False,'approved_for_imagegen':False,
                'reviewed_by_human':False})
            if len(results)>=limit:return results
    return results

def discover_all_sources(taxon:str,seen:set[str])->list[dict]:
    results=[];errors=[]
    try:results.extend(discover(taxon,seen))
    except Exception as exc:errors.append('INAT:'+type(exc).__name__)
    used=seen|{str(x.get('photo_key')) for x in results if x.get('photo_key')}
    available=max(0,15-len(seen)-len(results))
    if available:
        try:results.extend(discover_gbif(taxon,used,limit=min(12,available)))
        except Exception as exc:errors.append('GBIF:'+type(exc).__name__)
    used=seen|{str(x.get('photo_key')) for x in results if x.get('photo_key')}
    available=max(0,15-len(seen)-len(results))
    if available:
        try:results.extend(discover_commons(taxon,used,limit=min(12,available)))
        except Exception as exc:errors.append('COMMONS:'+type(exc).__name__)
    if errors and not results:raise ValueError('SOURCE_DISCOVERY_FAILED:'+','.join(errors))
    return results

def prioritize_reference_diversity(candidates:list[dict], prior:list[dict])->list[dict]:
    """Prefer distinct observations before extra frames from one observer event.

    Unverified observer text may influence research search order only.
    It does not assign a camera pose, behaviour, sex or readiness decision.
    """
    seen_previous={x.get('observation_id') for x in prior}
    ordered=sorted(enumerate(candidates),key=lambda item:(
        item[1].get('observation_id') in seen_previous,
        -len(item[1].get('unverified_observer_text_pose_hints') or []),
        -len(item[1].get('unverified_observer_behaviour_hints') or []),
        item[0]))
    primary=[];extras=[];seen_obs=set()
    for _,candidate in ordered:
        oid=candidate.get('observation_id')
        if oid not in seen_obs:
            primary.append(candidate);seen_obs.add(oid)
        else:
            extras.append(candidate)
    return primary+extras


def research_species(spec:dict,previous:dict,out:Path,max_per_species:int=12,discovery=discover_all_sources,download=fetch)->dict:
    taxon=spec['name'];key=spec['key'];old=(previous.get('species') or {}).get(key,{})
    prior=old.get('candidates',[]);old_leads=old.get('link_only_leads',[])
    seen={v.get('photo_key') for v in prior}|{v.get('photo_key') for v in old_leads}
    accepted=[];links=[];rejections=[];phashes=[];obs_counts={}
    max_additional=max(0,15-len(seen))
    # Every return is candidate-only; never auto-promote species, sex or licence.
    try: found=discovery(taxon,seen)
    except Exception as exc:
        return {'key':key,'taxon':taxon,'status':'RETRY_DISCOVERY','new_candidates':[],'new_link_leads':[], 'rejections':[str(exc)[:140]]}
    for c in prioritize_reference_diversity(found,prior+old_leads):
        if len(accepted)+len(links)>=max_additional:break
        if c.get('link_only') or c.get('license_code') not in ALLOWED:
            if len(links)<MAX_LINK_LEADS_PER_SPECIES_PER_CYCLE:
                # Link metadata is immediately useful for research and human
                # Gold review. Never download or archive unknown-rights pixels.
                links.append({k:v for k,v in c.items() if k!='thumbnail_url'}|
                  {'link_only':True,'research_use_status':'RESEARCH_LINK_AVAILABLE_NOW',
                   'media_copied_to_public_repo':False,'approved_for_imagegen':False})
            continue
        if len(accepted)>=max_per_species:continue
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
    return {'key':key,'taxon':taxon,'status':'REVIEW_REQUIRED' if accepted else ('LINK_RESEARCH_READY' if links else ('ALREADY_COLLECTED_OR_NO_NEW_LEADS' if (prior or old_leads) else 'NO_CANDIDATES')),
            'new_candidates':accepted,'new_link_leads':links,'rejections':rejections[:20],
            'camera_view_research_needs':research_needs(),
            'behaviour_research_hints_are_unverified':True}

def run(seed:dict,index:dict,shard:int,cycle:int,per_worker:int,limit:int,out:Path,**kwargs)->dict:
    specs=choose_species(seed,shard,cycle,per_worker,index)
    out.mkdir(parents=True,exist_ok=True);rows=[]
    for spec in specs:
        row=research_species(spec,index,out,limit,**kwargs);rows.append(row)
        print(spec['name'], row['status'],len(row['new_candidates']),flush=True)
    report={'schema':'VNMV1_PUBLIC_PHOTO_RESEARCH_SHARD_V1','shard':shard,'cycle':cycle,'species_processed':len(rows),
            'camera_view_research_standard':research_needs(),
            'downloaded_candidates':sum(len(r['new_candidates']) for r in rows),
            'new_link_only_research_leads':sum(len(r.get('new_link_leads',[])) for r in rows),
            'approvals':0,'imagegen_invocations':0,'species':rows}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--seed',type=Path,required=True);p.add_argument('--index',type=Path,required=True)
    p.add_argument('--extension',type=Path)
    p.add_argument('--shard',type=int,required=True);p.add_argument('--cycle',type=int,required=True)
    p.add_argument('--species-per-worker',type=int,default=4);p.add_argument('--max-photos',type=int,default=12)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if not 1<=a.max_photos<=18:raise SystemExit('Bad photo limit')
    seed=json.loads(a.seed.read_text())
    if a.extension:
        seed=merge_seed_with_extension(seed,json.loads(a.extension.read_text()))
    run(seed,json.loads(a.index.read_text()),a.shard,a.cycle,a.species_per_worker,a.max_photos,a.out)
if __name__=='__main__':main()