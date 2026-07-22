#!/usr/bin/env python3
"""Export selected sprite frames as grid, strip, ZIP, and manifest.

Frame exclusions affect playback and every export, matching Sprite Studio.
"""

from __future__ import annotations

import argparse
import json
import math
import zipfile
from pathlib import Path

from PIL import Image


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--animations-dir",type=Path,required=True); parser.add_argument("--action",required=True); parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--exclude",default="",help="1-based source frame numbers, comma separated")
    parser.add_argument("--prompt-file",type=Path)
    args=parser.parse_args(); source_manifest=json.loads((args.animations_dir/"manifest.json").read_text(encoding="utf-8")); animation=next((item for item in source_manifest["animations"] if item["name"]==args.action),None)
    if not animation: parser.error(f"action not found: {args.action}")
    excluded={int(value)-1 for value in args.exclude.split(",") if value.strip()}
    source_paths=[args.animations_dir/path for path in animation["frames"]]; active=[(index,path) for index,path in enumerate(source_paths) if index not in excluded]
    if not active: parser.error("at least one frame must remain")
    frames=[Image.open(path).convert("RGBA") for _,path in active]; cell=int(source_manifest["frameSize"]); cols=min(4,len(frames)); rows=math.ceil(len(frames)/cols)
    grid=Image.new("RGBA",(cols*cell,rows*cell),(0,0,0,0)); strip=Image.new("RGBA",(len(frames)*cell,cell),(0,0,0,0))
    for index,frame in enumerate(frames): grid.alpha_composite(frame,((index%cols)*cell,(index//cols)*cell)); strip.alpha_composite(frame,(index*cell,0))
    args.output_dir.mkdir(parents=True,exist_ok=True); grid_path=args.output_dir/"sheet.png"; strip_path=args.output_dir/"strip.png"; grid.save(grid_path); strip.save(strip_path)
    prompt=args.prompt_file.read_text(encoding="utf-8").strip() if args.prompt_file else ""
    manifest={"version":1,"bodyPlan":source_manifest.get("bodyPlan"),"anim":args.action,"frameCount":len(frames),"frameSize":cell,"fps":animation["fps"],"frameDurationMs":animation.get("frameDurationMs",round(1000/animation["fps"])),"loop":animation["loop"],"grid":{"fileName":"sheet.png","cols":cols,"rows":rows,"sheetWidth":cols*cell,"sheetHeight":rows*cell},"strip":{"fileName":"strip.png","cols":len(frames),"rows":1,"sheetWidth":len(frames)*cell,"sheetHeight":cell},"prompt":prompt,"excludedSourceFrames":[index+1 for index in sorted(excluded)],"frames":[{"index":index,"sourceIndex":source_index,"fileName":f"frame_{index+1:02d}.png","gridCol":index%cols,"gridRow":index//cols,"gridX":(index%cols)*cell,"gridY":(index//cols)*cell,"stripX":index*cell,"stripY":0} for index,(source_index,_) in enumerate(active)]}
    manifest_path=args.output_dir/"manifest.json"; manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    zip_path=args.output_dir/f"{args.action}_sprite.zip"
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as archive:
        for index,(_,path) in enumerate(active): archive.write(path,f"frame_{index+1:02d}.png")
        archive.write(grid_path,"sheet.png"); archive.write(strip_path,"strip.png"); archive.write(manifest_path,"manifest.json")
    print(zip_path)


if __name__=="__main__": main()
