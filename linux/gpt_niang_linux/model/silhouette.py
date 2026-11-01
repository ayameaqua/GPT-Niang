"""Monotone, layered silhouette registration, without mixing whole sprites."""
from bisect import bisect_right
import math

from PySide6.QtCore import QPointF,QRectF,Qt
from PySide6.QtGui import QImage,QPainter,QPainterPath,QPainterPathStroker,QPolygonF,QTransform

_MIPS={}


def mip_texture(painter,image,world_width,world_height):
    matrix=painter.worldTransform();scale=max(math.hypot(matrix.m11(),matrix.m12()),math.hypot(matrix.m21(),matrix.m22()))
    tw=min(image.width(),max(16,math.ceil(world_width*scale*1.5)))
    th=min(image.height(),max(16,math.ceil(world_height*scale*1.5)))
    key=(image.cacheKey(),tw,th)
    result=_MIPS.get(key)
    if result is None:
        result=image.scaled(tw,th,Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation)
        if len(_MIPS)>=48:del _MIPS[next(iter(_MIPS))]
        _MIPS[key]=result
    return result


def draw_quad(painter,image,source,target):
    """Safe textured convex quad, with affine triangles at a closing window."""
    source=QPolygonF([QPointF(*p) for p in source]);target=QPolygonF([QPointF(*p) for p in target])
    if any(not math.isfinite(v) or abs(v)>4096 for p in target for v in (p.x(),p.y())):return False
    # A skin/hair window can close to a line. An affine triangle cannot have a
    # projective horizon and safely paints the remaining nonzero area.
    painted=False
    for indices in ((0,1,2),(0,2,3)):
        a,b,c=(source[i] for i in indices);p,q,r=(target[i] for i in indices)
        ux,uy=b.x()-a.x(),b.y()-a.y();vx,vy=c.x()-a.x(),c.y()-a.y();det=ux*vy-vx*uy
        dx,dy=q.x()-p.x(),q.y()-p.y();ex,ey=r.x()-p.x(),r.y()-p.y()
        if abs(det)<1e-7 or abs(dx*ey-ex*dy)<1e-7:continue
        m11,m12=(dx*vy-ex*uy)/det,(dy*vy-ey*uy)/det
        m21,m22=(ex*ux-dx*vx)/det,(ey*ux-dy*vx)/det
        transform=QTransform(m11,m12,m21,m22,p.x()-m11*a.x()-m21*a.y(),p.y()-m12*a.x()-m22*a.y())
        painter.save()
        path=QPainterPath();path.addPolygon(QPolygonF([p,q,r]));path.closeSubpath()
        stroke=QPainterPathStroker();stroke.setWidth(1.2);path=path.united(stroke.createStroke(path))
        painter.setClipPath(path,Qt.ClipOperation.IntersectClip)
        painter.setTransform(transform,True)
        left=max(0,math.floor(min(a.x(),b.x(),c.x()))-2);top=max(0,math.floor(min(a.y(),b.y(),c.y()))-2)
        right=min(image.width(),math.ceil(max(a.x(),b.x(),c.x()))+2);bottom=min(image.height(),math.ceil(max(a.y(),b.y(),c.y()))+2)
        if right>left and bottom>top:
            region=QRectF(left,top,right-left,bottom-top);painter.drawImage(region,image,region)
        painter.restore();painted=True
    return painted


class RasterPalette:
    def __init__(self,image,box,anchor,crown_x=None,smooth_outline=False):
        rgba=image.convertToFormat(QImage.Format.Format_RGBA8888)
        alpha=bytes(rgba.constBits())[3::4].translate(bytes(0 if a<16 else 1 for a in range(256)))
        width,height=image.width(),image.height();rows=[]
        for y in range(height):
            row=alpha[y*width:(y+1)*width];left=row.find(b'\1');right=row.rfind(b'\1')
            rows.append((max(0,left-2),min(width,right+3)) if left>=0 else None)
        valid=[y for y,row in enumerate(rows) if row is not None]
        if not valid:raise ValueError('空的分层材质')
        top=max(0,valid[0]-2);bottom=min(height,valid[-1]+3)
        left=min(row[0] for row in rows if row);right=max(row[1] for row in rows if row)
        x,y,w,h=box
        self.box=(x+left/width*w,y+top/height*h,(right-left)/width*w,(bottom-top)/height*h)
        self.image=image.copy(left,top,right-left,bottom-top)
        self.anchor=tuple(anchor);self.crown_x=anchor[0] if crown_x is None else crown_x
        self.ys=(self.box[1],max(self.box[1]+.001,min(self.box[1]+self.box[3]-.001,anchor[1])),self.box[1]+self.box[3])
        first=rows[valid[0]];last=first;self.rows=[]
        for row in rows[top:bottom]:
            last=row or last
            self.rows.append((x+last[0]/width*w,x+last[1]/width*w))
        if smooth_outline:
            # The enclosing Lipschitz envelope keeps every source pixel, while
            # preventing a single disappearing curl tip from shifting an entire
            # scanline of hair or cloth by a hundred model units.
            left=[p[0] for p in self.rows];right=[p[1] for p in self.rows]
            step=self.box[3]/max(1,len(self.rows))*1.5
            for indices in (range(1,len(left)),range(len(left)-2,-1,-1)):
                for i in indices:
                    j=i-1 if indices.step>0 else i+1
                    left[i]=min(left[i],left[j]+step);right[i]=max(right[i],right[j]-step)
            self.rows=list(zip(left,right))

    def bounds(self,y):
        position=max(0.,min(len(self.rows)-1.,(y-self.box[1])/self.box[3]*(len(self.rows)-1)))
        index=int(position);a=self.rows[index];b=self.rows[min(index+1,len(self.rows)-1)];t=position-index
        left=a[0]+(b[0]-a[0])*t;right=a[1]+(b[1]-a[1])*t
        minimum=max(8.,self.box[2]*.035)
        if right-left<minimum:
            centre=(left+right)/2;left=centre-minimum/2;right=centre+minimum/2
        fraction=max(0.,min(1.,(y-self.ys[0])/max(.001,self.ys[1]-self.ys[0])))
        centre=self.crown_x+(self.anchor[0]-self.crown_x)*fraction
        centre=max(left+(right-left)*.1,min(right-(right-left)*.1,centre))
        return left,centre,right

    def warp(self,first,second,amount):return SilhouetteWarp(self,first,second,amount)


class SilhouetteWarp:
    def __init__(self,source,first,second,amount):
        self.source=source;self.first=first;self.second=second;self.amount=amount
        self.ys=tuple(a+(b-a)*amount for a,b in zip(first.ys,second.ys))

    @staticmethod
    def phase(y,ys):
        i=max(0,min(1,bisect_right(ys,y)-1))
        return i,(y-ys[i])/max(.001,ys[i+1]-ys[i])

    def row(self,index,t):
        a=self.first.ys[index]+(self.first.ys[index+1]-self.first.ys[index])*t
        b=self.second.ys[index]+(self.second.ys[index+1]-self.second.ys[index])*t
        return tuple(x+(y-x)*self.amount for x,y in zip(self.first.bounds(a),self.second.bounds(b)))

    def __call__(self,point):
        x,y=point;i,t=self.phase(y,self.source.ys)
        left,centre,right=self.source.bounds(y);tl,tc,tr=self.row(i,t)
        xx=tc+(x-centre)*((tc-tl)/max(.001,centre-left) if x<=centre else (tr-tc)/max(.001,right-centre))
        return xx,self.ys[i]+(self.ys[i+1]-self.ys[i])*t

    def inverse(self,point):
        x,y=point;i,t=self.phase(y,self.ys)
        yy=self.source.ys[i]+(self.source.ys[i+1]-self.source.ys[i])*t
        left,centre,right=self.source.bounds(yy);tl,tc,tr=self.row(i,t)
        xx=centre+(x-tc)*((centre-left)/max(.001,tc-tl) if x<=tc else (right-centre)/max(.001,tr-tc))
        return xx,yy


def draw_strips(painter,palette,warp,project=lambda point:point,rows=64,image=None):
    x,y,w,h=palette.box
    points=[project(warp((xx,y+h*row/rows))) for row in range(rows+1) for xx in palette.bounds(y+h*row/rows)]
    if any(not math.isfinite(value) or abs(value)>4096 for point in points for value in point):return rows*2
    left=math.floor(min(p[0] for p in points))-2;top=math.floor(min(p[1] for p in points))-2
    width=math.ceil(max(p[0] for p in points))-left+2;height=math.ceil(max(p[1] for p in points))-top+2
    if max(width,height)>2048:return rows*2
    canvas=QImage(width,height,QImage.Format.Format_ARGB32_Premultiplied);canvas.fill(Qt.GlobalColor.transparent)
    hp=QPainter(canvas);hp.setRenderHints(painter.renderHints());hp.translate(-left,-top)
    rejected=_draw_strips(hp,palette,warp,project,rows,image);hp.end()
    painter.drawImage(QPointF(left,top),canvas);return rejected


def _draw_strips(painter,palette,warp,project,rows,image):
    """Two monotone columns of convex quads; reject projective horizons."""
    texture=palette.image if image is None else image
    x,y,w,h=palette.box;matrix=painter.worldTransform()
    scale=max(math.hypot(matrix.m11(),matrix.m12()),math.hypot(matrix.m21(),matrix.m22()))
    tw=min(texture.width(),max(16,math.ceil(w*scale*1.5)))
    th=min(texture.height(),max(16,math.ceil(h*scale*1.5)))
    key=(texture.cacheKey(),tw,th);mip=_MIPS.get(key)
    if mip is None:
        mip=texture.scaled(tw,th,Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation)
        if len(_MIPS)>=32:del _MIPS[next(iter(_MIPS))]
        _MIPS[key]=mip
    # Work on shared vertices; neighboring strips have identical clip edges.
    vertices=[]
    for row in range(rows+1):
        yy=y+h*row/rows
        vertices.append([(xx,yy) for xx in palette.bounds(yy)])
    rejected=0
    for row in range(rows):
        for column in range(2):
            points=[vertices[rr][cc] for rr,cc in ((row,column),(row,column+1),(row+1,column+1),(row+1,column))]
            source=[((xx-x)/w*tw,(yy-y)/h*th) for xx,yy in points]
            target=[project(warp(point)) for point in points]
            rejected+=not draw_quad(painter,mip,source,target)
    return rejected
