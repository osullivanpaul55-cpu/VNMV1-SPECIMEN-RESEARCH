#!/usr/bin/env python3
"""Batch real public research reference images into photo-by-photo ChatGPT review packets.

This tool DOES NOT run a visual model or label any animal. It assembles exact
source-photo metadata and optional low-res contact sheets for human/ChatGPT
inspection; later draft labels require hash-verified visual evidence.
"""
import argparse
import io
import json
import math
import re
import urllib.request
from pathlib import Path

TRUSTED = ("static.inaturalist.org", "inaturalist-open-data.s3.amazonaws.com",
           "inaturalist-open-data.s3.us-west-2.amazonaws.com")
def allowed_image(url):
    from urllib.parse import urlsplit
    try:
        x=urlsplit(str(url))
        return x.scheme=="https" and x.hostname in TRUSTED and not x.username and not x.password
    except ValueError:
        return False

def entries(index):
    result={}
    for spec in index.get("species",{}).values():
        if not isinstance(spec,dict):continue
        taxon=spec.get("scientific_name") or "UNKNOWN"
        for photo in spec.get("candidates",[]) or []:
            key=photo.get("photo_key","")
            sha=photo.get("sha256","")
            if not re.fullmatch(r"inat:\d+",key) or not re.fullmatch(r"[0-9a-f]{64}",sha):continue
            if key in result:continue
            result[key]={"photo_key":key,"source_image_sha256":sha,
                "scientific_name":taxon,"source_url":photo.get("source_url"),
                "image_url":photo.get("thumbnail_url") if allowed_image(photo.get("thumbnail_url")) else None,
                "licence_code":photo.get("license_code","UNKNOWN"),
                "photographer":photo.get("attribution","UNKNOWN"),
                "image_available_for_visual_review":bool(allowed_image(photo.get("thumbnail_url"))),
                "visual_analysis_status":"NOT_VISUALLY_ANALYSED",
                "resemblance_status":"NOT_ASSESSED_PRIVATE_ORIGINAL",
                "requested_fields":["pose","sex_stage","visible_anatomy","behaviours",
                    "appearance","source_lighting","image_limits","possible_misidentification",
                    "visual_confidence","source_photo_evidence"]}
    return sorted(result.values(),key=lambda x:(x["scientific_name"],x["photo_key"]))

def sheet(rows,dest):
    from PIL import Image, ImageDraw, ImageOps
    cols=3; cellw=420; cellh=372
    canvas=Image.new("RGB",(cols*cellw,math.ceil(len(rows)/cols)*cellh),"#f4f6fa")
    draw=ImageDraw.Draw(canvas)
    for i,entry in enumerate(rows):
        left=(i%cols)*cellw;top=(i//cols)*cellh
        draw.rectangle([left,top,left+cellw-2,top+cellh-2],outline="#666666",width=2)
        url=entry.get("image_url")
        if url:
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"VNMV1 noncommercial research visual review (+source attribution)"})
                with urllib.request.urlopen(req,timeout=7) as r:
                    data=r.read(6_000_000)
                source=Image.open(io.BytesIO(data)).convert("RGB")
                source=ImageOps.contain(source,(cellw-14,cellh-90))
                canvas.paste(source,(left+(cellw-source.width)//2,top+5))
            except Exception as ex:entry["image_fetch_failed"]=str(ex)[:110]
        lines=[entry["photo_key"]+" · "+entry["scientific_name"][:30],
            entry["source_image_sha256"][:14]+" · "+str(entry["licence_code"])]
        for j,line in enumerate(lines):
            draw.text((left+6,top+cellh-57+j*21),line,fill="#111111")
    canvas.save(dest)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--index",default="data/index.json")
    p.add_argument("--out",default="visual-review-batch")
    p.add_argument("--start",type=int,default=0)
    p.add_argument("--count",type=int,default=12)
    p.add_argument("--contact-sheet",action="store_true")
    p.add_argument("--skip-reviewed",action="store_true",
                   help="Queue only photos without a validated ChatGPT visual draft in the review manifest")
    p.add_argument("--reviews",default="data/photo_visual_reviews.json")
    a=p.parse_args()
    pool=entries(json.loads(Path(a.index).read_text()))
    reviewed=set()
    if a.skip_reviewed:
        d=json.loads(Path(a.reviews).read_text())
        assert d.get("schema")=="VNMV1_PUBLIC_VISUAL_RECOMMENDATIONS_V1"
        for item in pool:
            known=d.get("photos",{}).get(item["photo_key"])
            if (isinstance(known,dict) and known.get("source_image_sha256")==item["source_image_sha256"]
                    and known.get("reviewed_actual_image") is True
                    and known.get("analysis_method")=="CHATGPT_VISUAL_DRAFT"):
                reviewed.add(item["photo_key"])
        pending=[item for item in pool if item["photo_key"] not in reviewed]
    else:
        pending=pool
    assert 0<=a.start and 1<=a.count<=36
    rows=pending[a.start:a.start+a.count]
    folder=Path(a.out);folder.mkdir(parents=True,exist_ok=True)
    manifest={"schema":"VNMV1_PHOTO_VISUAL_REVIEW_HANDOFF_V1",
      "total_indexed_public_candidates":len(pool),
      "already_visually_reviewed":len(reviewed),
      "remaining_unreviewed_candidates":len(pending),
      "selection_mode":"NEXT_UNREVIEWED" if a.skip_reviewed else "INDEX_OFFSET",
      "start":a.start,"count":len(rows),"model_visual_analysis_completed":0,
      "photo_review_items":rows,
      "import_contract":"data/photo_visual_reviews.json",
      "notice":"Reference images are not source specimen originals. Photo-based draft recommendations must be annotated after observing exact imagery; do not assert resemblance to private originals."}
    if a.contact_sheet and rows:sheet(rows,folder/"public_photo_contact_sheet.png")
    (folder/"review_packet.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(f"Queued {len(rows)} photo(s) from {len(pool)} total public candidates; {len(reviewed)} already visually reviewed; {len(pending)} pending; no visual approvals granted")
if __name__=="__main__":main()
