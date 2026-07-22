"""Body-plan, animation, and pose registry adapted from Sprite Studio.

Upstream: promptwhisper/sprite-generator@12a5c31 (MIT).
"""

from __future__ import annotations

import math


ACTIONS = {
    "idle": (6, True, "subtle breathing; calm stationary loop; frame 8 returns to frame 1"),
    "walk": (12, True, "contact, down, pass, high, then mirrored gait; opposing limbs; in place"),
    "run": (14, True, "strong forward lean, push-off, suspension and mirrored footfalls; in place"),
    "jump": (10, False, "neutral, crouch, launch, rise, apex, descend, land, recover"),
    "attack": (12, False, "combat stance, anticipation, wind-up, burst, impact, follow-through, recover"),
    "hurt": (8, False, "neutral, impact jolt, peak recoil, stagger, recover, settle"),
    "death": (10, False, "final hit, buckle, collapse, settle into a motionless final pose"),
    "pounce": (12, False, "alert, crouch, coil, explosive leap, airborne reach, descend, strike, recover"),
    "sleep": (4, True, "curled ground pose with slow ribcage breathing and a seamless loop"),
    "slither": (12, True, "one traveling sinusoidal wave advances tail-to-head over 8 frames"),
    "strike": (14, False, "coil back, load, fast head lunge with open mouth, overshoot, retract"),
    "coil": (10, False, "loose wave tightens into compact defensive coil and holds"),
    "flap": (12, True, "high spread wing, power downstroke, low sweep, folded recovery upstroke"),
    "glide": (8, True, "wings held extended with subtle tip flutter, tail correction and body drift"),
    "dive": (14, False, "pull up, tip down, wings tuck, plunge, flare and level out"),
    "hop": (10, True, "rest, squash, stretch launch, rise, apex, descend, impact squash, settle"),
    "bounce": (12, True, "higher snappier hop with stronger squash/stretch and impact"),
    "lunge": (12, False, "compress backward, stretch sharply forward, overshoot, snap back and settle"),
}

BODY_PLANS = {
    "biped": {
        "actions": ["idle", "walk", "run", "jump", "attack", "hurt", "death"],
        "scale_group": ["idle", "walk", "run"],
        "default": "idle",
        "airborne": {"jump"},
        "anchor": "upright humanoid idle, side profile facing right, feet planted, arms natural",
        "guidance": "match torso lean, head, arm swing, and each hip/knee bend; separate near/far limbs",
    },
    "quadruped": {
        "actions": ["idle", "walk", "run", "jump", "pounce", "hurt", "death", "sleep"],
        "scale_group": ["idle", "walk", "run"],
        "default": "idle",
        "airborne": {"jump", "pounce"},
        "anchor": "calm four-legged stance, side profile, head right, all four feet planted",
        "guidance": "match spine, neck, head, tail and all four legs; separate near/far legs",
    },
    "serpent": {
        "actions": ["idle", "slither", "strike", "coil", "hurt", "death"],
        "scale_group": ["idle", "slither"],
        "default": "idle",
        "airborne": set(),
        "anchor": "long limbless body in readable S-curve, side profile, head at right end",
        "guidance": "skin the mannequin tube as one continuous tapered body with head at right",
    },
    "flyer": {
        "actions": ["idle", "flap", "glide", "dive", "hurt", "death"],
        "scale_group": [],
        "default": "flap",
        "airborne": {"idle", "flap", "glide", "dive", "hurt", "death"},
        "anchor": "winged creature hovering in side profile facing right, both wings fully visible",
        "guidance": "match body pitch, head, tail and both wings; keep the creature airborne",
    },
    "blob": {
        "actions": ["idle", "hop", "bounce", "lunge", "hurt", "death"],
        "scale_group": [],
        "default": "idle",
        "airborne": {"hop", "bounce"},
        "anchor": "amorphous blob at rest, eyes right, rounded silhouette near the bottom",
        "guidance": "match squash, stretch, lean and width while preserving apparent volume",
    },
}


def limb(base, flex):
    return (base, flex)


def bpose(lean, body_y, leg_hip, leg_knee, arm_shoulder, arm_elbow, head=0, **overrides):
    value = {
        "lean": lean, "body_y": body_y,
        "leg_a": limb(leg_hip, leg_knee), "leg_b": limb(leg_hip, leg_knee),
        "arm_a": limb(arm_shoulder, arm_elbow), "arm_b": limb(arm_shoulder, arm_elbow),
        "head_tilt": head,
    }
    value.update(overrides)
    return value


def _arm_from_leg(hip, swing, elbow):
    base = -swing * hip
    return limb(base, elbow + 0.25 * abs(base))


def _biped_locomotion(curve, lean, bob, arm_swing, elbow):
    frames = []
    for index in range(8):
        a, b = curve[index], curve[(index + 4) % 8]
        theta = index / 8 * math.tau
        frames.append({
            "lean": lean, "body_y": bob * math.cos(2 * theta),
            "leg_a": limb(*a), "leg_b": limb(*b),
            "arm_a": _arm_from_leg(a[0], arm_swing, elbow),
            "arm_b": _arm_from_leg(b[0], arm_swing, elbow), "head_tilt": 0,
        })
    return frames


BIPED = {
    "idle": [
        bpose(3, 0, 4, 11, -4, 15), bpose(3, .004, 4, 10, -5, 15, -1),
        bpose(4, .009, 4, 9, -6, 16, -2), bpose(4, .013, 4, 8, -7, 16, -2),
        bpose(4, .009, 4, 9, -6, 16, -1), bpose(3, .004, 4, 10, -5, 15),
        bpose(2, -.005, 4, 13, -3, 14, 2), bpose(3, 0, 4, 11, -4, 15),
    ],
    "walk": _biped_locomotion([(25,5),(10,18),(-8,12),(-22,6),(-20,40),(-2,55),(18,35),(27,12)], 6, .018, .7, 18),
    "run": _biped_locomotion([(28,30),(5,18),(-26,35),(-34,95),(-8,110),(26,88),(40,52),(33,36)], 20, .05, .55, 75),
    "jump": [
        bpose(2,0,2,8,2,14), bpose(14,-.09,18,62,-42,30), bpose(6,.02,6,26,70,22),
        bpose(-4,.15,-8,48,120,18), bpose(-6,.23,-4,82,140,16,-4), bpose(2,.12,2,44,90,22),
        bpose(12,-.07,14,66,-20,28), bpose(4,0,4,16,6,16),
    ],
    "hurt": [bpose(4,0,4,10,4,16),bpose(-22,-.02,-10,30,-50,35,-18),bpose(-30,-.03,-16,42,-70,45,-24),bpose(-18,-.02,-8,30,-40,35,-14),bpose(-8,-.01,0,20,-20,25,-6),bpose(-2,0,4,14,-6,18),bpose(2,0,4,12,2,16),bpose(4,0,4,10,4,16)],
    "death": [bpose(-6,0,4,12,-10,30,-10),bpose(18,-.05,16,45,10,35,12),bpose(40,-.16,30,75,35,50,28),bpose(62,-.26,55,100,60,60,45),bpose(78,-.34,80,120,80,70,60),bpose(88,-.4,95,130,95,80,72),bpose(94,-.44,100,135,100,85,80),bpose(96,-.45,100,138,102,88,84)],
}
BIPED["attack"] = [
    {"lean":6,"body_y":0,"leg_a":(14,14),"leg_b":(-16,18),"arm_a":(30,60),"arm_b":(-10,30),"head_tilt":0},
    {"lean":-2,"body_y":.005,"leg_a":(8,16),"leg_b":(-20,22),"arm_a":(-50,80),"arm_b":(-20,25),"head_tilt":0},
    {"lean":-8,"body_y":.01,"leg_a":(4,18),"leg_b":(-26,28),"arm_a":(-95,95),"arm_b":(-28,20),"head_tilt":0},
    {"lean":10,"body_y":0,"leg_a":(20,16),"leg_b":(-18,24),"arm_a":(10,50),"arm_b":(0,28),"head_tilt":0},
    {"lean":22,"body_y":-.01,"leg_a":(32,18),"leg_b":(-24,12),"arm_a":(70,12),"arm_b":(20,30),"head_tilt":0},
    {"lean":16,"body_y":0,"leg_a":(28,18),"leg_b":(-22,16),"arm_a":(95,18),"arm_b":(18,30),"head_tilt":0},
    {"lean":8,"body_y":0,"leg_a":(18,16),"leg_b":(-18,20),"arm_a":(55,45),"arm_b":(0,28),"head_tilt":0},
    {"lean":6,"body_y":0,"leg_a":(14,14),"leg_b":(-16,18),"arm_a":(30,60),"arm_b":(-10,30),"head_tilt":0},
]


def qpose(body_y, back_tilt, front, hind, neck, head_tilt, tail, depth=6):
    return {"body_y":body_y,"back_tilt":back_tilt,"front_near":front,"front_far":(front[0]-depth,front[1]),"hind_near":hind,"hind_far":(hind[0]-depth,hind[1]),"neck":neck,"head_tilt":head_tilt,"tail":tail}


def _quad_walk():
    curve=[(22,12),(8,18),(-10,16),(-24,20),(-18,50),(-2,62),(14,42),(24,18)]
    out=[]
    for i in range(8):
        theta=i/8*math.tau
        out.append({"body_y":.02*math.cos(2*theta),"back_tilt":1.5*math.sin(theta),"hind_near":curve[i],"hind_far":curve[(i+4)%8],"front_near":curve[(i+2)%8],"front_far":curve[(i+6)%8],"neck":-40+5*math.sin(theta+math.pi/2),"head_tilt":2*math.sin(theta),"tail":18+6*math.sin(theta)})
    return out


QUADRUPED = {
    "idle":[qpose(0,0,(6,12),(-6,20),-42,0,18),qpose(.004,0,(6,11),(-6,19),-43,-1,16),qpose(.008,0,(6,10),(-6,18),-44,-1,14),qpose(.01,0,(6,10),(-6,18),-44,0,16),qpose(.008,0,(6,11),(-6,19),-43,0,18),qpose(.004,0,(6,12),(-6,20),-42,1,20),qpose(-.004,0,(6,13),(-6,21),-41,2,22),qpose(0,0,(6,12),(-6,20),-42,0,18)],
    "walk":_quad_walk(),
    "run":[qpose(-.04,-4,(10,70),(-20,64),-34,6,28,8),qpose(.02,-8,(-18,30),(-40,30),-28,4,6,8),qpose(.16,2,(34,18),(-46,22),-36,0,-18,6),qpose(.05,6,(40,22),(-22,40),-42,-2,-6,6),qpose(-.05,4,(26,16),(4,26),-40,2,12,8),qpose(.14,-2,(4,64),(18,70),-32,4,24,8),qpose(.02,-6,(-6,40),(30,40),-30,4,20,8),qpose(-.04,-4,(14,60),(-6,58),-34,6,26,8)],
    "jump":[qpose(0,0,(6,12),(-6,20),-42,0,18),qpose(-.08,-6,(16,60),(-22,64),-30,8,30),qpose(.04,8,(-14,28),(-30,26),-50,-6,-4),qpose(.2,6,(10,36),(-28,40),-48,-4,-16),qpose(.27,2,(22,30),(-26,34),-46,-2,-20),qpose(.12,-2,(30,24),(-10,30),-44,0,-6),qpose(-.07,4,(20,56),(4,60),-34,6,22),qpose(0,0,(6,14),(-6,22),-42,0,18)],
    "pounce":[qpose(-.02,-2,(8,18),(-8,24),-40,2,16),qpose(-.12,-10,(20,72),(-26,78),-22,14,34),qpose(-.06,-6,(26,50),(-34,48),-30,8,20),qpose(.1,10,(-30,18),(-40,22),-52,-8,-10),qpose(.22,8,(-40,14),(-30,28),-50,-6,-22),qpose(.12,4,(-20,12),(-10,34),-44,-2,-16),qpose(-.05,-4,(30,30),(10,40),-32,10,18),qpose(-.02,0,(10,18),(-6,24),-40,2,16)],
    "hurt":[qpose(0,0,(6,12),(-6,20),-42,0,18),qpose(-.03,10,(22,24),(-22,26),-20,18,8),qpose(-.05,14,(28,28),(-26,22),-14,22,2),qpose(-.03,8,(18,26),(-16,26),-26,12,10),qpose(-.01,3,(10,20),(-10,22),-36,6,16),qpose(0,0,(6,14),(-6,20),-40,2,18),qpose(0,0,(6,12),(-6,20),-42,0,18),qpose(0,0,(6,12),(-6,20),-42,0,18)],
    "death":[qpose(0,0,(6,12),(-6,20),-42,-4,16),qpose(-.06,-6,(18,40),(-18,46),-22,10,22),qpose(-.16,-10,(30,78),(-26,84),-8,20,18),qpose(-.26,-8,(44,110),(10,110),8,30,10),qpose(-.34,-4,(70,130),(40,128),22,42,4),qpose(-.4,0,(95,140),(80,138),40,56,-2),qpose(-.43,0,(108,146),(98,144),58,70,-4),qpose(-.45,0,(112,150),(104,148),70,78,-6)],
    "sleep":[qpose(-.36,0,(96,138),(92,140),64,60,-40),qpose(-.355,0,(96,137),(92,139),63,60,-40),qpose(-.35,0,(95,136),(91,138),62,59,-39),qpose(-.348,0,(95,136),(91,137),62,59,-39),qpose(-.35,0,(95,137),(91,138),63,60,-39),qpose(-.355,0,(96,137),(92,139),63,60,-40),qpose(-.36,0,(96,138),(92,140),64,61,-40),qpose(-.36,0,(96,138),(92,140),64,60,-40)],
}


def sp(phase, amp, freq, body_y, reach, head_tilt=0, mouth=0):
    return {"phase":phase,"amp":amp,"freq":freq,"body_y":body_y,"reach":reach,"head_tilt":head_tilt,"mouth":mouth}


SERPENT = {
    "idle":[sp(i/8*math.pi,.05+.008*math.sin(i/8*math.tau),1.4,0,0) for i in range(8)],
    "slither":[sp(i/8*math.tau,.13,2,0,0) for i in range(8)],
    "strike":[sp(0,.1,1.6,0,0),sp(.4,.18,2.2,0,-.1,-8),sp(.85,.24,2.7,0,-.2,-14,.18),sp(.55,.14,1.8,0,.12,4,.5),sp(.12,.06,1,0,.44,-12,1),sp(.22,.08,1.2,0,.34,-6,.7),sp(.42,.12,1.6,0,.1,0,.18),sp(0,.11,1.6,0,0)],
    "coil":[sp(0,.1,1.4,0,0),sp(.3,.14,1.9,0,-.05,-4),sp(.6,.17,2.6,-.02,-.12,-8),sp(.9,.2,3.3,-.03,-.18,-12),sp(1.1,.22,4,-.04,-.24,-16),sp(1.2,.23,4.5,-.05,-.28,-18,.12),sp(1.26,.24,4.8,-.05,-.3,-20,.12),sp(1.26,.24,4.8,-.05,-.3,-20,.12)],
    "hurt":[sp(0,.1,1.6,0,0),sp(1.2,.24,2.6,.02,-.08,-10),sp(2,.28,3,.01,-.1,-14),sp(1.4,.2,2.4,0,-.04,-8),sp(.8,.15,2,0,0,-4),sp(.4,.12,1.7,0,0),sp(.1,.1,1.6,0,0),sp(0,.1,1.6,0,0)],
    "death":[sp(0,.14,1.8,0,0,-6),sp(1.4,.22,2.4,.01,-.04,-12),sp(2.2,.16,2,0,0,6),sp(2.6,.1,1.6,-.01,0,14),sp(2.8,.06,1.2,-.02,0,22),sp(2.9,.035,.9,-.02,0,30),sp(3,.02,.6,-.03,0,36),sp(3,.012,.4,-.03,0,40)],
}


def fp(body_y, body_tilt, wing, tail, head_tilt=0, far_delta=8):
    return {"body_y":body_y,"body_tilt":body_tilt,"wing_near":wing,"wing_far":(wing[0]-far_delta,wing[1]),"tail":tail,"head_tilt":head_tilt}


FLYER = {
    "idle":[fp(0,-4,(40,30),14),fp(.01,-4,(55,24),12),fp(.015,-4,(62,20),10),fp(.01,-4,(48,28),12),fp(-.005,-4,(28,40),16),fp(-.01,-4,(14,52),18),fp(-.005,-4,(26,44),16),fp(0,-4,(38,34),14)],
    "flap":[fp(.04,6,(86,8),10),fp(-.01,7,(52,16),4),fp(-.04,9,(16,28),-4),fp(-.02,10,(-34,44),-10),fp(.05,8,(-12,56),-2),fp(.07,6,(26,44),6),fp(.06,6,(58,22),9),fp(.05,6,(82,10),10)],
    "glide":[fp(0,-2,(10,8),10),fp(.006,-2,(12,7),9),fp(.01,-3,(13,6),8),fp(.006,-3,(11,7),9),fp(0,-2,(9,8),10),fp(-.006,-2,(8,9),11),fp(-.01,-1,(7,10),12),fp(0,-2,(10,8),10)],
    "dive":[fp(.08,-6,(70,14),8),fp(.05,8,(30,24),0),fp(0,28,(-6,40),-10),fp(-.08,46,(-20,62),-18),fp(-.18,54,(-26,70),-22),fp(-.24,40,(-10,56),-12),fp(-.22,18,(20,34),2),fp(-.18,0,(55,18),10)],
    "hurt":[fp(0,-4,(40,30),14),fp(.03,-22,(85,6),28,-18),fp(.02,-28,(92,4),32,-24),fp(0,-18,(70,14),24,-14),fp(-.02,-10,(50,24),18,-6),fp(-.01,-6,(38,32),14),fp(0,-4,(40,30),14),fp(0,-4,(40,30),14)],
    "death":[fp(.02,-6,(60,18),12,-8),fp(-.04,18,(20,40),4,14),fp(-.14,60,(-20,80),-8,40),fp(-.26,110,(-40,110),-16,70),fp(-.36,150,(-50,130),-20,95),fp(-.43,175,(-55,140),-22,110),fp(-.46,182,(-58,145),-24,116),fp(-.47,184,(-58,146),-24,118)],
}


def bp(body_y, squash, skew=0, reach=0, eye_tilt=0):
    return {"body_y":body_y,"squash":squash,"skew":skew,"reach":reach,"eye_tilt":eye_tilt}


BLOB = {
    "idle":[bp(0,1),bp(0,1.02),bp(0,1.05),bp(0,1.03),bp(0,1),bp(0,.98),bp(0,.97),bp(0,1)],
    "hop":[bp(0,1),bp(0,1.32,.03,0,-4),bp(.06,.74,.05,0,8),bp(.17,.9,0,0,5),bp(.2,.97),bp(.1,.86,0,0,-3),bp(0,1.34,-.03,0,-6),bp(0,1.04)],
    "bounce":[bp(0,1),bp(0,1.52,.05,0,-7),bp(.08,.6,.08,0,12),bp(.27,.82,0,0,7),bp(.35,.93),bp(.14,.74,0,0,-5),bp(0,1.56,-.05,0,-9),bp(0,1.1)],
    "lunge":[bp(0,1),bp(0,1.24,-.12,0,4),bp(0,1.34,-.18,0,6),bp(0,.92,.12,.6,-4),bp(0,.78,.2,1.2,-10),bp(0,.88,.13,.7,-6),bp(0,1.14,-.03,.1,2),bp(0,1)],
    "hurt":[bp(0,1),bp(0,1.45,-.16,0,-14),bp(.02,.8,.1,0,12),bp(0,1.28,-.08,0,-8),bp(0,.92,.05),bp(0,1.08,-.02),bp(0,1),bp(0,1)],
    "death":[bp(0,1,0,0,-6),bp(.02,.88,0,0,-10),bp(0,1.35,0,.2),bp(0,1.7,0,.4),bp(0,2.05,0,.6),bp(0,2.35,0,.8),bp(0,2.55,0,.95),bp(0,2.65,0,1)],
}


POSES = {"biped": BIPED, "quadruped": QUADRUPED, "serpent": SERPENT, "flyer": FLYER, "blob": BLOB}
