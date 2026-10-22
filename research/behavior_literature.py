#!/usr/bin/env python3
"""Public-safe species literature discovery: publication leads only, never proof of behaviour or use rights."""
from __future__ import annotations
import argparse, json, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API="https://api.crossref.org/works"
UA="VNMV1-SPECIMEN-RESEARCH/1.2 (github.com/osullivanpaul55-cpu/VNMV1-SPECIMEN-RESEARCH; bibliographic research only)"
SCHEMA="VNMV1_PUBLIC_BEHAVIOUR_LITERATURE_CANDIDATES_V1"
MAX_TAXA_PER_RUN=24
DOI_PATTERN=re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")
def normalized(text):
    return re.sub(r"\s+"," ",re.sub(r"<[^>]{0,180}>"," ",str(text or ""))).strip()
def exact_species_mentioned(taxon,record):
    s=normalized((record.get("title") or [""])[0]+" "+record.get("abstract",""))
    return re.search(r"(?<![A-Za-z])"+re.escape(taxon)+r"(?![A-Za-z])",s,re.I) is not None
def safe_publication(record,taxon,lexicon):
    if not isinstance(record,dict) or not exact_species_mentioned(taxon,record):return None
    doi=record.get("DOI","")
    if not isinstance(doi,str) or not DOI_PATTERN.fullmatch(doi):return None
    title=normalized((record.get("title") or [""])[0])[:340]
    abstract=normalized(record.get("abstract",""))[:3000]
    haystack=(title+" "+abstract).lower()
    hints=[]
    for behavior in lexicon:
        terms=behavior.get("unverified_text_terms",[])
        if any(re.search(r"\b"+re.escape(term.lower())+r"\b",haystack) for term in terms):
            hints.append(behavior["id"])
    issued=record.get("issued",{})
    parts=(issued.get("date-parts") or [[]])[0] if isinstance(issued,dict) else []
    year=parts[0] if parts and isinstance(parts[0],int) else None
    return {"doi":doi,"url":"https://doi.org/"+doi,"title":title,"published_year":year,
       "behavior_text_hints_unverified":hints[:40],
       "evidence_scope":"BIBLIOGRAPHIC_SPECIES_TEXT_MENTION_NOT_EXPERT_REVIEW",
       "species_behavior_verified":False,"visual_pose_verified":False,
       "photo_source_verified":False,"photo_license_verified":False}
def get_crossref(taxon,fetch=None):
    url=API+"?"+urlencode({"query.bibliographic":taxon,"rows":7,"select":"DOI,title,abstract,issued,type,URL"})
    if fetch is None:
        def fetch(url):
            req=Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
            with urlopen(req,timeout=20) as resp:
                raw=resp.read(850_000+1)
                if len(raw)>850_000:raise ValueError("CROSSREF_RESPONSE_TOO_LARGE")
                return json.loads(raw)
    response=fetch(url)
    items=response.get("message",{}).get("items",[])
    if not isinstance(items,list):raise ValueError("CROSSREF_RESPONSE_INVALID")
    return items
def run(seed,index,terms,cycle,per_run=MAX_TAXA_PER_RUN,fetch=None):
    if seed.get("schema")!="VNMV1_PUBLIC_RESEARCH_SPECIES_SEED_V1":raise ValueError("INVALID_SEED")
    if index.get("schema")!=SCHEMA:raise ValueError("INVALID_INDEX")
    if len(seed["species"])!=len({x["key"] for x in seed["species"]}):raise ValueError("DUPLICATE_SPECIES_SEED")
    if not 0<=per_run<=MAX_TAXA_PER_RUN or cycle<0:raise ValueError("BAD_BATCH")
    names=seed["species"]
    start=cycle*per_run
    chosen=names[start:start+per_run]
    record=json.loads(json.dumps(index))
    results=record.setdefault("species",{})
    for entry in chosen:
        taxon=entry["name"]
        items=get_crossref(taxon,fetch=fetch)
        publications={}
        for item in items:
            p=safe_publication(item,taxon,terms)
            if p:publications[p["doi"].lower()]=p
        old=results.get(entry["key"],{})
        prev={v["doi"].lower():v for v in old.get("publication_leads",[]) if isinstance(v,dict) and v.get("doi")}
        prev.update(publications)
        results[entry["key"]]={"research_taxon":taxon,
          "taxon_key":entry["key"],"taxon_identity_status":"PUBLIC_RESEARCH_NAME_NOT_CARD_SPECIMEN_CERTIFIED",
          "publication_leads":list(prev.values())[:30],
          "no_automatic_behavior_confirmation":True,
          "no_media_or_rights_permissions_implied":True}
        if fetch is None:time.sleep(0.6)
    record["last_cycle"]=max(record.get("last_cycle",-1),cycle)
    record["last_research_at_utc"]=datetime.now(timezone.utc).isoformat()
    record["named_species_in_seed"]=len(names)
    record["species_with_literature_leads"]=sum(bool(x.get("publication_leads")) for x in results.values())
    record["species_searched"]=len(results)
    record["research_completed_first_sweep"]=len(results)==len(names)
    return record
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seed",type=Path,default=Path("research/species_seed.json"))
    p.add_argument("--index",type=Path,default=Path("data/behavior_literature_index.json"))
    p.add_argument("--terms",type=Path,default=Path("research/behavior_text_terms.json"))
    p.add_argument("--cycle",type=int,required=True)
    p.add_argument("--per-run",type=int,default=MAX_TAXA_PER_RUN)
    a=p.parse_args()
    seed=json.loads(a.seed.read_text());index=json.loads(a.index.read_text());terms=json.loads(a.terms.read_text())["behaviors"]
    out=run(seed,index,terms,a.cycle,a.per_run)
    a.index.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({key:out[key] for key in ("last_cycle","species_searched","species_with_literature_leads","research_completed_first_sweep")}))
if __name__=="__main__":main()
