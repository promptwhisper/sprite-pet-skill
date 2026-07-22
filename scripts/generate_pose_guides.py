#!/usr/bin/env python3
"""Render Sprite Studio's five deterministic 8-frame body-plan pose rigs.

Supports biped, quadruped, serpent, flyer, and blob. Adapted from
promptwhisper/sprite-generator@12a5c31 (MIT).
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

from sprite_methods import BODY_PLANS, POSES


COLORS = {"key":"#ff00ff","torso":"#525a66","near":"#9aa2af","far":"#2c313a","joint":"#1b1e24","outline":"#101218"}
AA = 2


def pt(point):
    return tuple(round(value * AA) for value in point)


def capsule(draw, start, end, width, color, outline=True):
    outer = max(1, round((width + (width * .28 if outline else 0)) * AA))
    inner = max(1, round(width * AA))
    if outline:
        draw.line((pt(start), pt(end)), fill=COLORS["outline"], width=outer, joint="curve")
    draw.line((pt(start), pt(end)), fill=color, width=inner, joint="curve")


def dot(draw, point, radius, color, outline=True):
    x, y = pt(point)
    if outline:
        outer = (radius + radius * .16) * AA
        draw.ellipse((x-outer,y-outer,x+outer,y+outer), fill=COLORS["outline"])
    inner = radius * AA
    draw.ellipse((x-inner,y-inner,x+inner,y+inner), fill=color)


def proj_down(point, length, angle):
    radians = math.radians(angle)
    return point[0] + length * math.sin(radians), point[1] + length * math.cos(radians)


def proj_up(point, length, angle):
    radians = math.radians(angle)
    return point[0] + length * math.sin(radians), point[1] - length * math.cos(radians)


def measure_subject(anchor, cell):
    fallback = {"height":round(cell*.78),"center_x":cell/2,"baseline":round(cell*.92)}
    if not anchor:
        return fallback
    image = Image.open(anchor).convert("RGBA").resize((cell, cell), Image.Resampling.LANCZOS)
    xs, ys = [], []
    for y in range(cell):
        for x in range(cell):
            r,g,b,a = image.getpixel((x,y))
            if a < 24 or (r > 180 and g < 95 and b > 180):
                continue
            xs.append(x); ys.append(y)
    if len(xs) < cell*cell/400:
        return fallback
    return {"height":max(ys)-min(ys)+1,"center_x":(min(xs)+max(xs))/2,"baseline":max(ys)}


def draw_biped(draw, frame, ox, oy, cell, subject):
    h=subject["height"]
    p={"thigh":.245,"shin":.245,"torso":.3,"neck":.05,"head":.075,"upper":.16,"fore":.15}
    hip_y=oy+subject["baseline"]-(p["thigh"]+p["shin"])*h*.96-frame["body_y"]*h
    hip_x=ox+subject["center_x"]
    shoulder=proj_up((hip_x,hip_y),p["torso"]*h,frame["lean"])
    head=proj_up(shoulder,(p["neck"]+p["head"])*h,frame["lean"]+frame["head_tilt"])
    leg_w=h*.085; arm_w=h*.055; torso_w=h*.15; sep=h*.015
    def leg(root, limb, color):
        knee=proj_down(root,p["thigh"]*h,limb[0]); foot=proj_down(knee,p["shin"]*h,limb[0]-limb[1])
        capsule(draw,root,knee,leg_w,color); capsule(draw,knee,foot,leg_w,color); dot(draw,knee,leg_w*.45,COLORS["joint"],False)
    def arm(root, limb, color):
        elbow=proj_down(root,p["upper"]*h,limb[0]); hand=proj_down(elbow,p["fore"]*h,limb[0]+limb[1])
        capsule(draw,root,elbow,arm_w,color); capsule(draw,elbow,hand,arm_w,color); dot(draw,elbow,arm_w*.45,COLORS["joint"],False)
    arm((shoulder[0]-sep,shoulder[1]),frame["arm_b"],COLORS["far"]); leg((hip_x-sep,hip_y),frame["leg_b"],COLORS["far"])
    capsule(draw,(hip_x,hip_y),shoulder,torso_w,COLORS["torso"]); dot(draw,(hip_x,hip_y),torso_w*.5,COLORS["torso"],False)
    leg((hip_x+sep,hip_y),frame["leg_a"],COLORS["near"])
    dot(draw,head,p["head"]*h,COLORS["torso"]); dot(draw,(head[0]+p["head"]*h*.85,head[1]),p["head"]*h*.28,COLORS["near"],False)
    arm((shoulder[0]+sep,shoulder[1]),frame["arm_a"],COLORS["near"])


def draw_quadruped(draw, frame, ox, oy, cell, subject):
    h=min(subject["height"]*.82,cell*.34); leg_w=h*.075; body_w=h*.32; head_r=h*.15
    baseline=min(subject["baseline"],cell*.9); center=(ox+cell/2,oy+baseline-.54*h*.92-frame["body_y"]*h)
    half=h/2; angle=math.radians(frame["back_tilt"])
    shoulder=(center[0]+half*math.cos(angle),center[1]-half*math.sin(angle)); hip=(center[0]-half*math.cos(angle),center[1]+half*math.sin(angle)); depth=h*.045
    def leg(root, limb, color):
        knee=proj_down(root,.27*h,limb[0]); foot=proj_down(knee,.27*h,limb[0]-limb[1])
        capsule(draw,root,knee,leg_w,color); capsule(draw,knee,foot,leg_w*.85,color); dot(draw,knee,leg_w*.42,COLORS["joint"],False); dot(draw,foot,leg_w*.5,color)
    leg((hip[0]-depth,hip[1]),frame["hind_far"],COLORS["far"]); leg((shoulder[0]-depth,shoulder[1]),frame["front_far"],COLORS["far"])
    ta=math.radians(frame["tail"]); tail1=(hip[0]-.26*h*math.cos(ta),hip[1]+.26*h*math.sin(ta)); tail2=(tail1[0]-.26*h*math.cos(ta+.25),tail1[1]+.26*h*math.sin(ta+.25))
    capsule(draw,hip,tail1,leg_w*.8,COLORS["far"]); capsule(draw,tail1,tail2,leg_w*.5,COLORS["far"])
    capsule(draw,hip,shoulder,body_w,COLORS["torso"]); dot(draw,hip,body_w*.5,COLORS["torso"],False); dot(draw,shoulder,body_w*.52,COLORS["torso"],False)
    na=math.radians(frame["neck"]); neck=(shoulder[0]+.38*h*math.cos(na),shoulder[1]+.38*h*math.sin(na))
    capsule(draw,shoulder,neck,body_w*.55,COLORS["torso"]); dot(draw,neck,head_r,COLORS["near"])
    sa=math.radians(frame["neck"]+70+frame["head_tilt"]); dot(draw,(neck[0]+head_r*.9*math.cos(sa),neck[1]+head_r*.9*math.sin(sa)),head_r*.42,COLORS["near"])
    leg((hip[0]+depth,hip[1]),frame["hind_near"],COLORS["near"]); leg((shoulder[0]+depth,shoulder[1]),frame["front_near"],COLORS["near"])


def poly_tube(draw, points, width_fn, color):
    for index in range(len(points)-1):
        width=width_fn(index/(len(points)-1)); capsule(draw,points[index],points[index+1],width,color)


def draw_serpent(draw, frame, ox, oy, cell, subject):
    length=cell*.82; base_x=ox+subject["center_x"]-length/2; mid_y=oy+subject["baseline"]-cell*.24-frame["body_y"]*cell
    points=[]
    for k in range(29):
        t=k/28; stretch=1+frame["reach"]*t*t; env=.45+.55*(1-t)
        points.append((base_x+t*length*stretch,mid_y+frame["amp"]*cell*math.sin(frame["freq"]*math.tau*t+frame["phase"])*env))
    body_w=cell*.12; poly_tube(draw,points,lambda t: body_w*(.32+.78*t),COLORS["torso"])
    head,neck=points[-1],points[-3]; dx,dy=head[0]-neck[0],head[1]-neck[1]; norm=math.hypot(dx,dy) or 1; ux,uy=dx/norm,dy/norm; hr=cell*.075; mouth=max(0,min(1,frame["mouth"])); angle=math.atan2(uy,ux)
    if mouth>.05:
        base=(head[0]+ux*hr*.6,head[1]+uy*hr*.6); tip=(base[0]+ux*hr*(1.1+mouth*1.2),base[1]+uy*hr*(1.1+mouth*1.2)); capsule(draw,base,tip,cell*.009,COLORS["joint"],False)
    dot(draw,head,hr,COLORS["near"])
    if mouth>.05:
        gap=math.radians(8+mouth*42); capsule(draw,head,(head[0]+math.cos(angle-gap)*hr*1.05,head[1]+math.sin(angle-gap)*hr*1.05),hr*.5,COLORS["near"]); capsule(draw,head,(head[0]+math.cos(angle+gap)*hr*1.05,head[1]+math.sin(angle+gap)*hr*1.05),hr*.42,COLORS["torso"])
    else: dot(draw,(head[0]+ux*hr*.7,head[1]+uy*hr*.7),hr*.42,COLORS["near"])
    dot(draw,(head[0]+hr*.1,head[1]-hr*.35),hr*.22,COLORS["joint"],False)


def draw_flyer(draw, frame, ox, oy, cell, subject):
    center=(ox+subject["center_x"],oy+cell*.46-frame["body_y"]*cell); length=cell*.34; body_w=cell*.16; upper=cell*.3; lower=cell*.28; wing_w=cell*.05
    bt=math.radians(frame["body_tilt"]); head=(center[0]+length/2*math.cos(bt),center[1]+length/2*math.sin(bt)); rear=(center[0]-length/2*math.cos(bt),center[1]-length/2*math.sin(bt)); shoulder=(center[0]+length*.12*math.cos(bt),center[1]+length*.12*math.sin(bt))
    def wing(limb,color,membrane):
        angle=math.radians(limb[0]); elbow=(shoulder[0]-upper*math.cos(angle),shoulder[1]-upper*math.sin(angle)); tip=(elbow[0]-lower*math.cos(angle-math.radians(limb[1])),elbow[1]-lower*math.sin(angle-math.radians(limb[1]))); trail=(shoulder[0]-length*.34*math.cos(bt),shoulder[1]-length*.34*math.sin(bt))
        draw.polygon([pt(shoulder),pt(elbow),pt(tip),pt(trail)],fill=membrane,outline=COLORS["outline"],width=max(1,round(cell*.012*AA))); capsule(draw,shoulder,elbow,wing_w,color); capsule(draw,elbow,tip,wing_w*.7,color); dot(draw,elbow,wing_w*.5,COLORS["joint"],False)
    wing(frame["wing_far"],COLORS["torso"],COLORS["far"])
    ta=bt+math.pi+math.radians(frame["tail"]); tail=(rear[0]+cell*.22*math.cos(ta),rear[1]+cell*.22*math.sin(ta)); capsule(draw,rear,tail,wing_w*1.1,COLORS["far"])
    capsule(draw,rear,head,body_w,COLORS["torso"]); dot(draw,center,body_w*.55,COLORS["torso"],False)
    hr=cell*.085; hp=(head[0]+hr*.3*math.cos(bt),head[1]+hr*.3*math.sin(bt)); dot(draw,hp,hr,COLORS["near"]); ba=bt+math.radians(frame["head_tilt"]); dot(draw,(hp[0]+hr*math.cos(ba),hp[1]+hr*math.sin(ba)),hr*.45,COLORS["near"]); dot(draw,(hp[0]+hr*.25,hp[1]-hr*.2),hr*.22,COLORS["joint"],False)
    wing(frame["wing_near"],COLORS["torso"],COLORS["near"])


def draw_blob(draw, frame, ox, oy, cell, subject):
    r0=cell*.28; rx=r0*frame["squash"]*(1+frame["reach"]*.5); ry=r0/frame["squash"]*(1-frame["reach"]*.18); cx=ox+subject["center_x"]+frame["skew"]*r0+frame["reach"]*r0*.6; cy=oy+subject["baseline"]-ry-frame["body_y"]*cell
    points=[]
    for index in range(41):
        angle=index/40*math.tau; flat=.86 if 0<angle<math.pi else 1; bulge=1+.06*math.cos(angle); points.append(pt((cx+math.cos(angle)*rx*bulge,cy+math.sin(angle)*ry*flat)))
    draw.polygon(points,fill=COLORS["torso"],outline=COLORS["outline"],width=max(1,round(cell*.012*AA)))
    dot(draw,(cx-rx*.35,cy-ry*.4),min(rx,ry)*.32,COLORS["near"],False)
    eye=min(rx,ry)*.2; ex=cx+rx*.42; ey=cy-ry*.28+math.sin(math.radians(frame["eye_tilt"]))*eye
    dot(draw,(ex,ey),eye,COLORS["near"]); dot(draw,(ex+eye*.2,ey),eye*.5,COLORS["joint"],False); dot(draw,(ex-rx*.3,ey),eye*.85,COLORS["near"]); dot(draw,(ex-rx*.3+eye*.1,ey),eye*.42,COLORS["joint"],False)


DRAWERS={"biped":draw_biped,"quadruped":draw_quadruped,"serpent":draw_serpent,"flyer":draw_flyer,"blob":draw_blob}


def render(body_plan, action, output, cell, subject):
    # Render into oversized transparent scratch cells first. Some authored
    # extreme poses intentionally extend beyond the nominal cell; measuring the
    # union lets us apply ONE shared fit transform to the whole action instead
    # of clipping limbs or independently destroying the vertical motion arc.
    frames=POSES[body_plan][action]; scratch_size=cell*3*AA; scratches=[]; boxes=[]
    for frame in frames:
        scratch=Image.new("RGBA",(scratch_size,scratch_size),(0,0,0,0)); draw=ImageDraw.Draw(scratch)
        DRAWERS[body_plan](draw,frame,cell,cell,cell,subject); scratches.append(scratch)
        box=scratch.getchannel("A").getbbox()
        if box: boxes.append(box)
    if not boxes: raise ValueError(f"empty pose guide: {body_plan}/{action}")
    union=(min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)); margin=cell*AA*.04; available=cell*AA-2*margin
    scale=min(1,available/max(1,union[2]-union[0]),available/max(1,union[3]-union[1])); target_x=cell*AA/2; source_x=(union[0]+union[2])/2
    if body_plan=="flyer": target_y=cell*AA/2; source_y=(union[1]+union[3])/2
    else: target_y=cell*AA*.94; source_y=union[3]
    fitted=[]
    for scratch in scratches:
        resized=scratch.resize((max(1,round(scratch.width*scale)),max(1,round(scratch.height*scale))),Image.Resampling.LANCZOS) if scale<1 else scratch
        frame_cell=Image.new("RGBA",(cell*AA,cell*AA),(0,0,0,0)); frame_cell.alpha_composite(resized,(round(target_x-source_x*scale),round(target_y-source_y*scale))); fitted.append(frame_cell)
    canvas=Image.new("RGB",(cell*4*AA,cell*2*AA),COLORS["key"])
    for index,frame_cell in enumerate(fitted): canvas.paste(frame_cell,((index%4)*cell*AA,(index//4)*cell*AA),frame_cell)
    canvas=canvas.resize((cell*4,cell*2),Image.Resampling.LANCZOS); target=output/f"pose-{body_plan}-{action}.png"; canvas.save(target); return target


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-plan",choices=BODY_PLANS,required=True)
    parser.add_argument("--actions",default="all",help="comma list or all")
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--anchor",type=Path,help="raw magenta anchor used to match scale/baseline")
    parser.add_argument("--cell-size",type=int,default=512)
    args=parser.parse_args()
    actions=BODY_PLANS[args.body_plan]["actions"] if args.actions=="all" else [x.strip() for x in args.actions.split(",") if x.strip()]
    unknown=sorted(set(actions)-set(BODY_PLANS[args.body_plan]["actions"]))
    if unknown: parser.error(f"unsupported for {args.body_plan}: {', '.join(unknown)}")
    args.output_dir.mkdir(parents=True,exist_ok=True); subject=measure_subject(args.anchor,args.cell_size)
    for action in actions: print(render(args.body_plan,action,args.output_dir,args.cell_size,subject))


if __name__=="__main__":
    main()
