#!/usr/bin/env python3
"""
sam_corners.py - propose frame-opening quads with MobileSAM (operator confirms).

Strategy: generate several candidate seed points (centroids of the largest
bright, non-border-connected regions - the paper/mat inside a frame), run SAM
from each, and keep the mask that best matches a real print opening:
rectangular, print-like aspect (~0.7), and not a big chunk of the plate. Nothing
is written to OPENINGS.json; every result is an overlay to confirm.
"""
from __future__ import annotations
import sys, json
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from mobile_sam import sam_model_registry, SamPredictor

ROOT = Path(__file__).resolve().parent
MOCKS = ROOT / "assets" / "mockups"
PRINT_ASPECT = 3508/4961   # 0.707

_p=None
def predictor():
    global _p
    if _p is None:
        sam = sam_model_registry["vit_t"](checkpoint=str(ROOT/"models/mobile_sam.pt"))
        sam.to("cpu").eval(); _p = SamPredictor(sam)
    return _p

def bright_components(g, k=6):
    """Centroids of the k largest bright regions not touching the border."""
    thr = np.percentile(g, 80)
    mask = g > thr
    H,W = mask.shape
    # kill border-connected
    seen=np.zeros_like(mask,bool); dq=deque()
    for x in range(W):
        for y in (0,H-1):
            if mask[y,x]: dq.append((y,x))
    for y in range(H):
        for x in (0,W-1):
            if mask[y,x]: dq.append((y,x))
    while dq:
        y,x=dq.popleft()
        if y<0 or x<0 or y>=H or x>=W or seen[y,x] or not mask[y,x]: continue
        seen[y,x]=True; dq.extend(((y+1,x),(y-1,x),(y,x+1),(y,x-1)))
    interior = mask & ~seen
    # label components
    lab=np.zeros_like(interior,int); cur=0; comps=[]
    for sy in range(0,H,2):
        for sx in range(0,W,2):
            if interior[sy,sx] and not lab[sy,sx]:
                cur+=1; q=deque([(sy,sx)]); pts=[]
                while q:
                    y,x=q.popleft()
                    if y<0 or x<0 or y>=H or x>=W or lab[y,x] or not interior[y,x]: continue
                    lab[y,x]=cur; pts.append((x,y)); q.extend(((y+1,x),(y-1,x),(y,x+1),(y,x-1)))
                if len(pts)>80: comps.append(pts)
    comps.sort(key=len, reverse=True)
    seeds=[(int(np.mean([p[0] for p in c])), int(np.mean([p[1] for p in c]))) for c in comps[:k]]
    seeds.append((W//2,H//2))
    return seeds

def quad_from_mask(m):
    ys,xs=np.nonzero(m); s,d=xs+ys,xs-ys
    return [[int(xs[s.argmin()]),int(ys[s.argmin()])],[int(xs[d.argmax()]),int(ys[d.argmax()])],
            [int(xs[s.argmax()]),int(ys[s.argmax()])],[int(xs[d.argmin()]),int(ys[d.argmin()])]]

def score(m):
    area=m.sum()
    if area < 0.015*m.size or area > 0.55*m.size: return -1,None
    ys,xs=np.nonzero(m); w=xs.max()-xs.min()+1; h=ys.max()-ys.min()+1
    rect=area/(w*h)
    asp=w/h
    aspmatch=max(0,1-abs(asp-PRINT_ASPECT)/0.35)   # 1 at 0.707, 0 beyond +-0.35
    if rect<0.80: return -1,None
    return rect*0.5+aspmatch*0.5, None

def detect(pid):
    img=Image.open(MOCKS/f"px_{pid}.jpg").convert("RGB")
    scale=1024/max(img.size)
    small=img.resize((int(img.width*scale),int(img.height*scale)))
    sarr=np.asarray(small); g=sarr.mean(2)
    p=predictor(); p.set_image(sarr)
    best=(-1,None)
    for seed in bright_components(g):
        masks,scores,_=p.predict(point_coords=np.array([seed]),point_labels=np.array([1]),multimask_output=True)
        for m in masks:
            sc,_=score(m)
            if sc>best[0]: best=(sc,m)
    if best[1] is None: return None,-1
    q=quad_from_mask(best[1])
    return [[int(x/scale),int(y/scale)] for x,y in q], round(best[0],3)

if __name__=="__main__":
    pids=sys.argv[1:] or ['4466652','5726035','5978718','8101038','8490187','8490229','8490259','8534254','8947628']
    out={}
    for pid in pids:
        try:
            q,sc=detect(pid); out[pid]={"quad":q,"score":sc}
            print(f"{pid}: score {sc}  {q}", flush=True)
        except Exception as e:
            print(pid,"ERR",e,flush=True)
    (ROOT/"assets/mockups/pexels/SAM_proposed.json").write_text(json.dumps(out,indent=1))
    print("saved SAM_proposed.json")
