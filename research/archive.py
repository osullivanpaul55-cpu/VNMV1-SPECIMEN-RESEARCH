#!/usr/bin/env python3
"""Build persistent GitHub Release assets and a review-only public index.
No private card identity data, credentials, or user specimen photographs.
"""
from __future__ import annotations
import argparse, hashlib, json, re, zipfile
from pathlib import Path

SCHEMA='VNMV1_PUBLIC_PHOTO_CANDIDATES_V1'; MAX_SOURCE_LINK_LEADS_PER_SPECIES=100
def digest(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def compile_archive(shard_root:Path,previous:dict,out:Path,tag:str,repo:str)->dict:
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',tag):raise ValueError('BAD_RELEASE_TAG')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):raise ValueError('BAD_REPO')
    if previous.get('schema')!=SCHEMA:raise ValueError('BAD_INDEX')
    out.mkdir(parents=True,exist_ok=True)
    reports=sorted(shard_root.glob('shard-*/report.json'))
    if len(reports)!=5:raise ValueError(f'FIVE_SHARD_REPORTS_REQUIRED_{len(reports)}')
    docs=[json.loads(x.read_text()) for x in reports]
    if {r['shard'] for r in docs}!={0,1,2,3,4}:raise ValueError('SHARD_DUPLICATE_OR_MISSING')
    if len({r['cycle'] for r in docs})!=1:raise ValueError('CYCLE_MISMATCH')
    cycle=docs[0]['cycle'];index=json.loads(json.dumps(previous));species=index.setdefault('species',{})
    sha_seen={c.get('sha256') for row in species.values() for c in row.get('candidates',[])}
    key_seen={c.get('photo_key') for row in species.values() for c in row.get('candidates',[])}
    newly_added=0;links_added=0;assets=[]
    for src,report in zip(reports,docs):
        shard=report['shard'];asset_name=f'shard-{shard}.zip';asset=out/asset_name
        added=[]
        with zipfile.ZipFile(asset,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for row in report['species']:
                key=row['key'];taxon=row['taxon'];dest=species.setdefault(key,{'scientific_name':taxon,'research_only':True,'candidates':[],'last_state':'PENDING'})
                if dest['scientific_name']!=taxon:raise ValueError('SPECIES_KEY_COLLISION')
                dest['last_state']=row['status'];dest['last_cycle']=cycle
                link_leads=dest.setdefault('link_only_leads',[])
                prior_keys={x.get('photo_key') for x in link_leads}
                for lead in row.get('new_link_leads',[]):
                    lkey=lead.get('photo_key');lurl=lead.get('source_url')
                    if not isinstance(lkey,str) or not re.fullmatch(r'inat:[0-9]{1,15}',lkey):
                        raise ValueError('BAD_LINK_PHOTO_KEY')
                    if not isinstance(lurl,str) or not re.fullmatch(r'https://www\.inaturalist\.org/observations/[0-9]{1,15}',lurl):
                        raise ValueError('BAD_LINK_OBSERVATION')
                    if lkey in prior_keys or lkey in key_seen:continue
                    if lead.get('license_code') in ('cc0','cc-by') and lead.get('redistribution_allowed_by_collector'):
                        raise ValueError('ELIGIBLE_PHOTO_MISCLASSIFIED_AS_LINK')
                    if len(link_leads)>=MAX_SOURCE_LINK_LEADS_PER_SPECIES:break
                    # Do not carry source-photo pixels, derivatives or archives
                    # into metadata-only research entries.
                    public={k:v for k,v in lead.items() if k not in
                      ('thumbnail_url','archive_url','archive_member','sha256','bytes','width','height')}
                    public.update({'link_only':True,'media_copied_to_public_repo':False,
                        'research_use_status':'RESEARCH_LINK_AVAILABLE_NOW',
                        'approved_for_imagegen':False})
                    link_leads.append(public);prior_keys.add(lkey);links_added+=1
                for c in row['new_candidates']:
                    path=c['archive_member']
                    if not re.fullmatch(r'media/(?:[0-9a-f]{16}|[0-9a-f]{32})/[0-9]{1,15}\.(jpg|png|webp)',path):raise ValueError('BAD_ARCHIVE_MEMBER')
                    file=(src.parent/path).resolve()
                    if not file.is_relative_to(src.parent.resolve()) or not file.is_file():raise ValueError('REFERENCE_BYTES_MISSING')
                    b=file.read_bytes()
                    if digest(b)!=c['sha256']:raise ValueError('HASH_MISMATCH:'+path)
                    if c['photo_key'] in key_seen or c['sha256'] in sha_seen:continue
                    if c.get('license_code') not in ('cc0','cc-by') or not c.get('attribution') or not c.get('source_url'):
                        raise ValueError('ATTRIBUTION_OR_RIGHTS_EVIDENCE_MISSING')
                    url=f'https://github.com/{repo}/releases/download/{tag}/{asset_name}'
                    record={k:v for k,v in c.items() if k not in ('photo_identity','independent_photo_status')}
                    record.update({'archive_url':url,'archive_sha256':None,'archive_asset':asset_name,
                                   'license_verification':'PENDING_HUMAN_SOURCE_CHECK',
                                   'species_sex_anatomy_review':'PENDING','approved_for_imagegen':False})
                    z.writestr(path,b)
                    dest['candidates'].append(record)
                    dest['link_only_leads']=[x for x in link_leads if x.get('photo_key')!=c['photo_key']]
                    key_seen.add(c['photo_key']);sha_seen.add(c['sha256']);added.append({'taxon':taxon,'photo_key':c['photo_key'],'sha256':c['sha256'],'filename':path,'attribution':c['attribution'],'license_code':c['license_code'],'source_url':c['source_url']})
                    newly_added+=1
            z.writestr('CREDITS.json',json.dumps({'status':'RESEARCH_CANDIDATES_NOT_APPROVED','records':added},indent=2)+'\n')
        # Asset SHA available separately for audit; per-photo hashes remain immutable.
        assets.append({'filename':asset_name,'sha256':digest(asset.read_bytes()),'photos':len(added)})
    index.update({'schema':SCHEMA,'last_cycle':cycle,'image_generation_connected':False,
                  'approved_photo_count':0,'discovered_candidate_count':sum(len(x['candidates']) for x in species.values()),
                  'unlicensed_link_research_lead_count':sum(len(x.get('link_only_leads',[])) for x in species.values())})
    (out/'index.json').write_text(json.dumps(index,indent=2,ensure_ascii=False)+'\n')
    (out/'release_manifest.json').write_text(json.dumps({'schema':'VNMV1_PUBLIC_PHOTO_RELEASE_V1','tag':tag,'repo':repo,
         'cycle':cycle,'assets':assets,'new_candidate_count':newly_added,
         'new_research_link_lead_count':links_added,'approved_photo_count':0},indent=2)+'\n')
    return {'cycle':cycle,'new_candidate_count':newly_added,'new_link_research_leads':links_added,
            'index_total':index['discovered_candidate_count'],
            'total_link_research_leads':index['unlicensed_link_research_lead_count'],'assets':assets}

def main():
    a=argparse.ArgumentParser();a.add_argument('--shards',type=Path,required=True);a.add_argument('--index',type=Path,required=True)
    a.add_argument('--out',type=Path,required=True);a.add_argument('--tag',required=True);a.add_argument('--repo',required=True);args=a.parse_args()
    print(json.dumps(compile_archive(args.shards,json.loads(args.index.read_text()),args.out,args.tag,args.repo)))
if __name__=='__main__':main()