"""Small authored skeletal/projection functions, independent of Qt and time."""
import math


def mix(a, b, t):
    return a + (b-a)*t


def rotate(point, angle):
    c, s = math.cos(angle), math.sin(angle)
    return point[0]*c-point[1]*s, point[0]*s+point[1]*c


def coccyx_point(view_angle, seated=0.):
    """Posterior attachment follows pelvic pitch, not the dangling skirt hem."""
    p=max(0.,min(1.,seated));pitch=p*p*(3-2*p)*math.pi/2
    return 425+(50+31*math.sin(pitch))*math.sin(math.radians(view_angle)),652+31*math.cos(pitch)


def solve_leg(hip, ankle, upper, lower, bend=1, view_angle=90):
    """Two-bone IK, with an explicit knee side and no accumulating transforms."""
    dx, dy = ankle[0]-hip[0], ankle[1]-hip[1]
    distance = max(1e-5, math.hypot(dx, dy))
    reach = min(upper+lower-.05, max(abs(upper-lower)+.05, distance))
    ux, uy = dx/distance, dy/distance
    along = (upper*upper-lower*lower+reach*reach)/(2*reach)
    across = math.sqrt(max(0, upper*upper-along*along))*bend
    # The knee bends in the character's sagittal plane. Front/back flexion
    # goes into depth; it must not become an outward screen-space frog squat.
    forward=(-math.sin(math.radians(view_angle)),0.,math.cos(math.radians(view_angle)))
    dot=forward[0]*ux+forward[1]*uy
    perpendicular=(forward[0]-dot*ux,forward[1]-dot*uy,forward[2])
    norm=max(1e-6,math.sqrt(sum(v*v for v in perpendicular)))
    px,py,pz=(v/norm for v in perpendicular)
    knee = hip[0]+ux*along+px*across, hip[1]+uy*along+py*across, pz*across
    return knee, (hip[0]+ux*reach, hip[1]+uy*reach,0.)


def skin_point(point, rest, posed, weights):
    """Linear blend of rigid bone transforms; the boot is its own rigid bone."""
    out = [0., 0.]
    for index, weight in enumerate(weights):
        if weight <= 0:
            continue
        a, b = rest[index:index+2]
        c, d = posed[index:index+2]
        length=max(1e-6,math.hypot(b[0]-a[0],b[1]-a[1]))
        tx,ty=d[0]-c[0],d[1]-c[1];projected=max(1e-6,math.hypot(tx,ty))
        ux,uy=(b[0]-a[0])/length,(b[1]-a[1])/length
        dx,dy=point[0]-a[0],point[1]-a[1]
        along=(dx*ux+dy*uy)*projected/length;cross=-dx*uy+dy*ux
        out[0] += (c[0]+along*tx/projected-cross*ty/projected)*weight
        out[1] += (c[1]+along*ty/projected+cross*tx/projected)*weight
    return tuple(out)


def head_point(point, neck, box, pitch, yaw, view):
    """Limited 2.5D head pitch/yaw; neck is fixed, features share the surface.

    Forehead/face have depth, ears/outline approach the rear shell, and horn tips
    sit behind it. A profile's sagittal pitch becomes actual neck rotation.
    This is limited to small angles; it does not invent unseen head surfaces.
    """
    if abs(pitch)+abs(yaw)<1e-8:
        return tuple(point)
    x, y = point; nx, ny = neck
    direction = -1 if view in ('left','front-left','back-left') else 1
    if view in ('left','right'):
        angle = math.radians(pitch*direction)
        xx, yy = rotate((x-nx, y-ny), angle)
        bx,by,bw,bh=box
        forward=max(0.,min(1.,(x-nx)*direction/(bw*.45)))
        depth=bw*.22*max(0.,1-((y-(by+bh*.65))/(bh*.38))**2)**2*forward
        q=math.radians(yaw)
        return nx+xx*math.cos(q)+depth*math.sin(q), ny+yy
    bx, by, bw, bh = box
    cx = bx+bw*.5
    # A C1 rounded depth cap keeps the face-to-hair boundary fold-free. The
    # neck itself is a separate body-owned layer, rather than face pixels.
    u = (x-cx)/(bw*.48)
    ramp=min(1.,max(0.,(y-by-bh*.24)/(bh*.24)))
    ramp=ramp*ramp*(3-2*ramp)
    depth=bw*.27*max(0,1-u*u)**2*ramp-bw*.045*(1-ramp)
    p, q = math.radians(pitch), math.radians(yaw)
    # Existing three-quarter views already contain a yaw; limit the additional
    # surface turn, rather than replacing them with a second head silhouette.
    if view in ('front-left','front-right'):
        depth *= .85
    xx = nx+(x-nx)*math.cos(q)+depth*math.sin(q)
    yy = ny+(y-ny)*math.cos(p)+depth*math.sin(p)
    return xx, yy


VIEW_ANGLES = {'front':0,'front-left':45,'left':90,'back-left':135,
               'back':180,'back-right':225,'right':270,'front-right':315}
