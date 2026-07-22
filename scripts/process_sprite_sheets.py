#!/usr/bin/env python3
"""Run Sprite Studio's production sprite-sheet post-processing pipeline.

Order: normalize sheet size → slice → cast-based chroma key + despill → remove
cell borders → isolate duplicate components → median scale normalization →
grounded/airborne baseline alignment → alpha-centroid horizontal centering →
frames, grid, strip, diagnostics, and manifest.

Adapted from promptwhisper/sprite-generator@12a5c31 (MIT).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import median

from PIL import Image

from sprite_methods import ACTIONS, BODY_PLANS


ALPHA_THRESHOLD=64


def names(value): return [item.strip() for item in value.split(",") if item.strip()]


def parse_hex(value):
    value=value.strip().lstrip("#")
    if len(value)!=6: raise argparse.ArgumentTypeError("color must be #RRGGBB")
    try: return tuple(int(value[i:i+2],16) for i in (0,2,4))
    except ValueError as exc: raise argparse.ArgumentTypeError("color must be #RRGGBB") from exc


def chroma_key(image,key,cast_threshold=80,cast_softness=30,despill=1,green_boost=.5,key_tolerance=90,key_softness=60):
    rgba=image.convert("RGBA"); out=[]; magenta=key==(255,0,255)
    for r,g,b,source_alpha in rgba.getdata():
        if magenta:
            cast=max(0,min(r,b)-g); floor=max(0,cast_threshold-cast_softness)
            if cast>=cast_threshold: alpha=0
            elif cast<=floor: alpha=source_alpha
            else: alpha=round(source_alpha*(1-(cast-floor)/max(1,cast_threshold-floor)))
            if cast and despill:
                reduction=cast*despill; r=max(0,round(r-reduction)); b=max(0,round(b-reduction)); g=min(255,round(g+reduction*green_boost))
        else:
            distance=math.sqrt((r-key[0])**2+(g-key[1])**2+(b-key[2])**2)
            if distance<=key_tolerance: alpha=0
            elif distance>=key_tolerance+key_softness: alpha=source_alpha
            else: alpha=round(source_alpha*(distance-key_tolerance)/max(1,key_softness))
        out.append((r,g,b,alpha))
    result=Image.new("RGBA",rgba.size); result.putdata(out); return result


def remove_border(image,coverage=.7,band_fraction=.03,threshold=24):
    image=image.copy(); alpha=image.getchannel("A"); px=alpha.load(); w,h=image.size; band=max(2,round(min(w,h)*band_fraction)); row_need=round(w*coverage); col_need=round(h*coverage)
    for k in range(band):
        for y in (k,h-1-k):
            if sum(px[x,y]>threshold for x in range(w))>=row_need:
                for x in range(w): px[x,y]=0
        for x in (k,w-1-k):
            if sum(px[x,y]>threshold for y in range(h))>=col_need:
                for y in range(h): px[x,y]=0
    image.putalpha(alpha); return image


def label_components(mask,w,h):
    labels=[-1]*(w*h); components=[]
    for start in range(w*h):
        if not mask[start] or labels[start]>=0: continue
        cid=len(components); labels[start]=cid; stack=[start]; count=sum_x=sum_y=0
        while stack:
            point=stack.pop(); x=point%w; y=point//w; count+=1; sum_x+=x; sum_y+=y
            for neighbour in (point-1 if x else -1,point+1 if x+1<w else -1,point-w if y else -1,point+w if y+1<h else -1):
                if neighbour>=0 and mask[neighbour] and labels[neighbour]<0: labels[neighbour]=cid; stack.append(neighbour)
        components.append({"id":cid,"count":count,"sum_x":sum_x,"sum_y":sum_y})
    return labels,components


def erode(mask,w,h,iterations):
    current=mask
    for _ in range(iterations):
        result=bytearray(w*h)
        for y in range(1,h-1):
            for x in range(1,w-1):
                i=y*w+x
                if current[i] and current[i-1] and current[i+1] and current[i-w] and current[i+w]: result[i]=1
        current=result
    return current


def dilate(mask,w,h,iterations):
    current=mask
    for _ in range(iterations):
        result=bytearray(current)
        for y in range(h):
            for x in range(w):
                i=y*w+x
                if current[i]: continue
                if (x and current[i-1]) or (x+1<w and current[i+1]) or (y and current[i-w]) or (y+1<h and current[i+w]): result[i]=1
        current=result
    return current


def isolate_primary(image,enable_split=False,threshold=32,min_fraction=.005):
    alpha=image.getchannel("A"); w,h=image.size; values=alpha.tobytes(); mask=bytearray(1 if value>threshold else 0 for value in values); labels,components=label_components(mask,w,h); min_pixels=max(24,round(w*h*min_fraction)); real=[c for c in components if c["count"]>=min_pixels]
    if not real: return image
    def score(component):
        cx=component["sum_x"]/component["count"]; cy=component["sum_y"]/component["count"]; distance=math.hypot((cx-w/2)/w,(cy-h/2)/h); return component["count"]*(1+max(0,.35-distance))
    keep_mask=None
    if len(real)>=2:
        keep=max(real,key=score); keep_mask=bytearray(1 if label==keep["id"] else 0 for label in labels)
    elif enable_split:
        only=real[0]; radius=max(2,round(min(w,h)*.01)); eroded=erode(mask,w,h,radius); e_labels,cores=label_components(eroded,w,h); core_min=max(min_pixels*.5,only["count"]*.12); cores=[core for core in cores if core["count"]>=core_min]
        if len(cores)>=2:
            keep=max(cores,key=score); core_mask=bytearray(1 if label==keep["id"] else 0 for label in e_labels); keep_mask=dilate(core_mask,w,h,radius+1)
    if keep_mask is None: return image
    rgba=image.copy(); data=list(rgba.getdata()); rgba.putdata([(r,g,b,a if keep_mask[i] else 0) for i,(r,g,b,a) in enumerate(data)]); return rgba


def cleanup_detached_fragments(image,threshold=8,max_relative_area=.02,max_pixels=512):
    """Remove tiny disconnected spillover without hiding a second real subject/limb."""
    alpha=image.getchannel("A"); w,h=image.size; values=alpha.tobytes(); mask=bytearray(1 if value>threshold else 0 for value in values); labels,components=label_components(mask,w,h)
    if len(components)<=1: return image,{"componentCount":len(components),"removedPixels":0,"removedComponents":[]}
    primary=max(components,key=lambda component:component["count"]); limit=max(16,round(min(max_pixels,primary["count"]*max_relative_area))); removed=[component for component in components if component["id"]!=primary["id"] and component["count"]<=limit]
    if not removed: return image,{"componentCount":len(components),"removedPixels":0,"removedComponents":[]}
    removed_ids={component["id"] for component in removed}; removal=bytearray(1 if label in removed_ids else 0 for label in labels); removal=dilate(removal,w,h,2); rgba=image.copy(); data=list(rgba.getdata()); rgba.putdata([(r,g,b,0 if removal[i] else a) for i,(r,g,b,a) in enumerate(data)])
    return rgba,{"componentCount":len(components),"removedPixels":sum(component["count"] for component in removed),"removedComponents":sorted((component["count"] for component in removed),reverse=True)}


def alpha_bbox(image,threshold=ALPHA_THRESHOLD,noise_floor=3):
    alpha=image.getchannel("A"); w,h=image.size; values=alpha.tobytes(); rows=[0]*h; cols=[0]*w
    for y in range(h):
        start=y*w
        for x in range(w):
            if values[start+x]>threshold: rows[y]+=1; cols[x]+=1
    xs=[i for i,count in enumerate(cols) if count>=noise_floor]; ys=[i for i,count in enumerate(rows) if count>=noise_floor]
    return (min(xs),min(ys),max(xs)+1,max(ys)+1) if xs and ys else None


def translate(image,dx,dy):
    out=Image.new("RGBA",image.size,(0,0,0,0)); out.alpha_composite(image,(dx,dy)); return out


def normalize_scale(frames,tolerance=.05,max_adjust=.18):
    boxes=[alpha_bbox(frame) for frame in frames]; sizes=[math.hypot(box[2]-box[0],box[3]-box[1]) if box else -1 for box in boxes]; valid=sorted(size for size in sizes if size>0)
    if not valid: return frames,{"targetSize":None,"sizes":sizes,"scales":[1]*len(frames)}
    target=valid[len(valid)//2]; output=[]; scales=[]
    for image,box,size in zip(frames,boxes,sizes):
        if not box or size<=0: output.append(image); scales.append(1); continue
        factor=max(1-max_adjust,min(1+max_adjust,target/size))
        if abs(factor-1)<tolerance: output.append(image); scales.append(1); continue
        subject=image.crop(box); resized=subject.resize((max(1,round(subject.width*factor)),max(1,round(subject.height*factor))),Image.Resampling.LANCZOS); cx=(box[0]+box[2])/2; cy=(box[1]+box[3])/2; canvas=Image.new("RGBA",image.size,(0,0,0,0)); canvas.alpha_composite(resized,(round(cx-resized.width/2),round(cy-resized.height/2))); output.append(canvas); scales.append(factor)
    return output,{"targetSize":target,"sizes":sizes,"scales":scales}


def frame_bottom(image,threshold=64,min_row_pixels=4):
    alpha=image.getchannel("A"); w,h=image.size; values=alpha.tobytes(); counts=[sum(values[y*w+x]>threshold for x in range(w)) for y in range(h)]; run_rows=max(3,round(h*.012))
    for y in range(h-1,-1,-1):
        if counts[y]>=min_row_pixels and all(counts[y-k]>=min_row_pixels for k in range(run_rows) if y-k>=0) and y-run_rows+1>=0: return y
    for y in range(h-1,-1,-1):
        if counts[y]: return y
    return -1


def align_baseline(frames,airborne,target):
    detected=[frame_bottom(frame) for frame in frames]; valid=sorted(value for value in detected if value>=0)
    if not valid: return frames,{"targetBaseline":None,"detected":detected,"shifted":[0]*len(frames)}
    if airborne: ground_ref=valid[min(len(valid)-1,round((len(valid)-1)*.85))]; rigid=target-ground_ref
    output=[]; shifts=[]
    for frame,bottom in zip(frames,detected):
        shift=0 if bottom<0 else (rigid if airborne else target-bottom); output.append(translate(frame,0,shift) if shift else frame); shifts.append(shift)
    return output,{"targetBaseline":target,"detected":detected,"shifted":shifts}


def center_frames(frames):
    output=[]; detected=[]; shifts=[]
    for frame in frames:
        alpha=frame.getchannel("A"); w,h=frame.size; values=alpha.tobytes(); xs=[]
        for y in range(h):
            for x in range(w):
                if values[y*w+x]>32: xs.append(x)
        center=sum(xs)/len(xs) if len(xs)>=24 else -1; shift=0 if center<0 else max(-round(w*.4),min(round(w*.4),round(w/2-center))); output.append(translate(frame,shift,0) if shift else frame); detected.append(center); shifts.append(shift)
    return output,{"targetCenterX":frames[0].width/2 if frames else None,"detected":detected,"shifted":shifts}


def compose(frames,columns,rows,cell,strip=False):
    canvas=Image.new("RGBA",((len(frames) if strip else columns)*cell,(1 if strip else rows)*cell),(0,0,0,0))
    for index,frame in enumerate(frames): canvas.alpha_composite(frame,((index if strip else index%columns)*cell,(0 if strip else index//columns)*cell))
    return canvas


def process_action(args,action,airborne):
    source=args.input_dir/f"{args.prefix}{action}{args.suffix}"
    if not source.is_file(): raise FileNotFoundError(f"missing source sheet: {source}")
    expected=(args.columns*args.cell_size,args.rows*args.cell_size); sheet=Image.open(source).convert("RGBA")
    if sheet.size!=expected: sheet=sheet.resize(expected,Image.Resampling.LANCZOS)
    frames=[]; component_info=[]
    for index in range(args.columns*args.rows):
        col,row=index%args.columns,index//args.columns; cell=sheet.crop((col*args.cell_size,row*args.cell_size,(col+1)*args.cell_size,(row+1)*args.cell_size)); cell=chroma_key(cell,args.key_color,args.cast_threshold,args.cast_softness,args.despill,args.despill_green_boost,args.key_tolerance,args.key_softness); cell=remove_border(cell)
        if args.component_cleanup and args.body_plan!="biped": cell=isolate_primary(cell,enable_split=args.body_plan in {"quadruped","blob"})
        if args.detached_fragment_cleanup: cell,components=cleanup_detached_fragments(cell,max_relative_area=args.fragment_max_relative_area,max_pixels=args.fragment_max_pixels)
        else: components={"componentCount":None,"removedPixels":0,"removedComponents":[]}
        component_info.append(components)
        frames.append(cell)
    frames,scale_info=normalize_scale(frames); frames,baseline_info=align_baseline(frames,airborne,round(args.cell_size*.9)); frames,center_info=center_frames(frames)
    output=args.output_dir/action; output.mkdir(parents=True,exist_ok=True); paths=[]
    for index,frame in enumerate(frames):
        target=output/f"frame-{index:02d}.png"; frame.save(target); paths.append(f"{action}/frame-{index:02d}.png")
    compose(frames,args.columns,args.rows,args.cell_size).save(output/"sheet.png"); compose(frames,args.columns,args.rows,args.cell_size,True).save(output/"strip.png")
    fps,loop,_=ACTIONS[action]
    return {"name":action,"fps":fps,"frameDurationMs":round(1000/fps),"loop":loop,"airborne":airborne,"frameCount":len(frames),"frames":paths,"frameMeta":[{"index":i,"sourceIndex":i,"file":path} for i,path in enumerate(paths)],"exports":{"grid":f"{action}/sheet.png","strip":f"{action}/strip.png"},"processing":{"components":component_info,"scale":scale_info,"baseline":baseline_info,"center":center_info},"source":str(source)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir",type=Path,required=True); parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--body-plan",choices=BODY_PLANS,default="quadruped"); parser.add_argument("--actions",default="all"); parser.add_argument("--prefix",default=""); parser.add_argument("--suffix",default=".png")
    parser.add_argument("--columns",type=int,default=4); parser.add_argument("--rows",type=int,default=2); parser.add_argument("--cell-size",type=int,default=512)
    parser.add_argument("--key-color",type=parse_hex,default=parse_hex("#ff00ff")); parser.add_argument("--cast-threshold",type=int,default=80); parser.add_argument("--cast-softness",type=int,default=30); parser.add_argument("--despill",type=float,default=1); parser.add_argument("--despill-green-boost",type=float,default=.5); parser.add_argument("--key-tolerance",type=int,default=90); parser.add_argument("--key-softness",type=int,default=60)
    parser.add_argument("--component-cleanup",action=argparse.BooleanOptionalAction,default=True)
    parser.add_argument("--detached-fragment-cleanup",action=argparse.BooleanOptionalAction,default=True)
    parser.add_argument("--fragment-max-relative-area",type=float,default=.02)
    parser.add_argument("--fragment-max-pixels",type=int,default=512)
    args=parser.parse_args(); supported=BODY_PLANS[args.body_plan]["actions"]; actions=supported if args.actions=="all" else names(args.actions); unknown=sorted(set(actions)-set(supported))
    if unknown: parser.error(f"unsupported for {args.body_plan}: {', '.join(unknown)}")
    if args.columns*args.rows!=8: parser.error("Sprite Studio rigs require exactly 8 cells")
    if not 0<=args.fragment_max_relative_area<=1: parser.error("fragment max relative area must be between 0 and 1")
    if args.fragment_max_pixels<0: parser.error("fragment max pixels must be non-negative")
    args.output_dir.mkdir(parents=True,exist_ok=True); animations=[process_action(args,action,action in BODY_PLANS[args.body_plan]["airborne"]) for action in actions]
    manifest={"version":2,"bodyPlan":args.body_plan,"frameSize":args.cell_size,"grid":{"columns":args.columns,"rows":args.rows},"animations":animations,"provenance":"promptwhisper/sprite-generator@12a5c31"}; target=args.output_dir/"manifest.json"; target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(target)


if __name__=="__main__": main()
