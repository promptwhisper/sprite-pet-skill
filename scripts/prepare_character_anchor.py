#!/usr/bin/env python3
"""Normalize an uploaded character into Sprite Studio's 512px magenta anchor.

Removes border-connected checkerboard or solid backgrounds, preserves proper
transparency, scales into an 84%×90% safe area, and seats at a 95% baseline.
Adapted from promptwhisper/sprite-generator@12a5c31 (MIT).
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image


def remove_uploaded_background(image, transparent_skip=.02):
    rgba=image.convert("RGBA"); w,h=rgba.size; pixels=rgba.load(); total=w*h
    transparent=sum(1 for y in range(h) for x in range(w) if pixels[x,y][3]<200)
    if transparent/total>transparent_skip: return rgba
    corners=[pixels[0,0][:3],pixels[w-1,0][:3],pixels[0,h-1][:3],pixels[w-1,h-1][:3]]
    average=tuple(round(sum(c[i] for c in corners)/4) for i in range(3))
    spread=max(max(abs(c[i]-average[i]) for i in range(3)) for c in corners); solid=spread<24
    def background(x,y):
        r,g,b,a=pixels[x,y]
        if a<16: return True
        checker=max(r,g,b)>175 and max(r,g,b)-min(r,g,b)<38
        corner=solid and sum(abs(v-average[i]) for i,v in enumerate((r,g,b)))<60
        return checker or corner
    visited=bytearray(total); queue=deque()
    def push(x,y):
        index=y*w+x
        if visited[index]: return
        visited[index]=1
        if background(x,y): queue.append((x,y))
    for x in range(w): push(x,0); push(x,h-1)
    for y in range(h): push(0,y); push(w-1,y)
    while queue:
        x,y=queue.pop(); r,g,b,_=pixels[x,y]; pixels[x,y]=(r,g,b,0)
        if x: push(x-1,y)
        if x+1<w: push(x+1,y)
        if y: push(x,y-1)
        if y+1<h: push(x,y+1)
    return rgba


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input",type=Path)
    parser.add_argument("--output",type=Path,required=True,help="raw magenta anchor PNG")
    parser.add_argument("--transparent-output",type=Path,help="optional cleaned transparent PNG")
    parser.add_argument("--size",type=int,default=512)
    args=parser.parse_args()
    image=Image.open(args.input).convert("RGBA")
    max_dim=1024
    if max(image.size)>max_dim:
        scale=max_dim/max(image.size); image=image.resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.LANCZOS)
    cleaned=remove_uploaded_background(image)
    box=cleaned.getchannel("A").getbbox()
    if not box: parser.error("no character content remains after background cleanup")
    subject=cleaned.crop(box); limit_w=args.size*.84; limit_h=args.size*.90; scale=min(limit_w/subject.width,limit_h/subject.height)
    subject=subject.resize((max(1,round(subject.width*scale)),max(1,round(subject.height*scale))),Image.Resampling.LANCZOS)
    x=round((args.size-subject.width)/2); y=round(args.size*.95-subject.height)
    transparent=Image.new("RGBA",(args.size,args.size),(0,0,0,0)); transparent.alpha_composite(subject,(x,y))
    raw=Image.new("RGBA",(args.size,args.size),(255,0,255,255)); raw.alpha_composite(transparent)
    args.output.parent.mkdir(parents=True,exist_ok=True); raw.convert("RGB").save(args.output)
    if args.transparent_output:
        args.transparent_output.parent.mkdir(parents=True,exist_ok=True); transparent.save(args.transparent_output)
    print(args.output)


if __name__=="__main__":
    main()
