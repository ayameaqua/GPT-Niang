"""Authored three-piece arm geometry; no texture or colour-based joint guesses."""
import math


def endpoint(root, length, angle):
    """Angles use a downward rest axis, matching the neutral source pieces."""
    angle=math.radians(angle)
    return root[0]-math.sin(angle)*length,root[1]+math.cos(angle)*length


def arm_chain(spec, sizes, shoulder, lift, point=0., sway=0., base_angle=0., mirror=False):
    """Return connected shoulder/elbow/wrist transforms at constant bone lengths.

    Forearm and wrist have independent world angles, so waving moves the wrist
    without sweeping the sleeve/upper arm. Mirroring acts on each limb, never on
    the entire character or the anatomical hand IDs.
    """
    sign=-1 if mirror else 1
    upper=-12+(12-98)*lift+(-120+98)*point
    lower=12+(-162-12)*lift+(-130+162)*point
    wrist=-166*lift+sway
    angles=(upper,lower,wrist)
    root=tuple(shoulder);result={}
    for name,angle in zip(('upper','forearm','hand'),angles):
        segment=spec['segments'][name];w,h=sizes[name];scale=segment['scale']
        u,v=segment['rootUV'];eu,ev=segment['endUV']
        dx=(eu-u)*w*scale;dy=(ev-v)*h*scale
        length=math.hypot(dx,dy)
        target=sign*angle+base_angle
        source_angle=math.degrees(math.atan2(-sign*dx,dy))
        rotation=target-source_angle
        result[name]={'root':root,'end':endpoint(root,length,target),'rotation':rotation,
                      'box':[root[0]-(1-u if mirror else u)*w*scale,root[1]-v*h*scale,w*scale,h*scale],
                      'flipX':mirror}
        root=result[name]['end']
    return result
