"""Project the existing raster through a shared vertex grid; no artwork painting."""
import math
from PySide6.QtCore import QPointF,QRectF,Qt
from PySide6.QtGui import QImage,QPainter,QPainterPath,QPainterPathStroker,QPolygonF,QTransform

_MIPS={}
_CELLS={}


def draw_mesh(painter,image,box,map_point,columns=6,rows=16):
    x,y,w,h=box
    vertices=[[map_point((x+w*c/columns,y+h*r/rows)) for c in range(columns+1)] for r in range(rows+1)]
    points=[p for row in vertices for p in row];transform=painter.worldTransform()
    dw=(max(p[0] for p in points)-min(p[0] for p in points))*((transform.m11()**2+transform.m12()**2)**.5)
    dh=(max(p[1] for p in points)-min(p[1] for p in points))*((transform.m21()**2+transform.m22()**2)**.5)
    tw=min(image.width(),max(16,int(dw*1.5/16+1)*16));th=min(image.height(),max(16,int(dh*1.5/16+1)*16))
    if tw<image.width() or th<image.height():
        key=(image.cacheKey(),tw,th);mip=_MIPS.get(key)
        if mip is None:
            mip=image.scaled(tw,th,Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation)
            if len(_MIPS)>=48:del _MIPS[next(iter(_MIPS))]
            _MIPS[key]=mip
        image=mip
    sw,sh=image.width(),image.height()
    key=(image.cacheKey(),columns,rows);occupied=_CELLS.get(key)
    if occupied is None:
        rgba=image.convertToFormat(QImage.Format.Format_RGBA8888);alpha=bytes(rgba.constBits())[3::4]
        occupied=[]
        for row in range(rows):
            line=[];top=max(0,int(sh*row/rows)-2);bottom=min(sh,int(sh*(row+1)/rows)+3)
            for column in range(columns):
                left=max(0,int(sw*column/columns)-2);right=min(sw,int(sw*(column+1)/columns)+3)
                line.append(any(any(alpha[yy*sw+left:yy*sw+right]) for yy in range(top,bottom)))
            occupied.append(line)
        if len(_CELLS)>=96:del _CELLS[next(iter(_CELLS))]
        _CELLS[key]=occupied
    original=painter
    left=min(p[0] for p in points)-2;top=min(p[1] for p in points)-2
    right=max(p[0] for p in points)+2;bottom=max(p[1] for p in points)+2
    if max(right-left,bottom-top)>4096:return
    output=QImage(max(1,int(right-left+1)),max(1,int(bottom-top+1)),QImage.Format.Format_ARGB32_Premultiplied)
    output.fill(Qt.GlobalColor.transparent)
    painter=QPainter(output);painter.translate(-left,-top)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing,False)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,True)
    for r in range(rows):
        for c in range(columns):
            if not occupied[r][c]:continue
            sx,sy,ew,eh=sw*c/columns,sh*r/rows,sw/columns,sh/rows
            source=QPolygonF([QPointF(sx,sy),QPointF(sx+ew,sy),QPointF(sx+ew,sy+eh),QPointF(sx,sy+eh)])
            target=QPolygonF([QPointF(*vertices[rr][cc]) for rr,cc in ((r,c),(r,c+1),(r+1,c+1),(r+1,c))])
            # Affine triangles cannot acquire a projective horizon when the
            # silhouette folds. A projective quad could spill an infinite wedge.
            for indices in ((0,1,2),(0,2,3)):
                s0,s1,s2=(source[i] for i in indices);d0,d1,d2=(target[i] for i in indices)
                ux,uy=s1.x()-s0.x(),s1.y()-s0.y();vx,vy=s2.x()-s0.x(),s2.y()-s0.y()
                det=ux*vy-vx*uy
                ax,ay=d1.x()-d0.x(),d1.y()-d0.y();bx,by=d2.x()-d0.x(),d2.y()-d0.y()
                if abs(ax*by-bx*ay)<.001:continue
                a,b=(ax*vy-bx*uy)/det,(ay*vy-by*uy)/det
                c,d=(bx*ux-ax*vx)/det,(by*ux-ay*vx)/det
                transform=QTransform(a,b,c,d,d0.x()-a*s0.x()-c*s0.y(),d0.y()-b*s0.x()-d*s0.y())
                painter.save();painter.setTransform(transform,True)
                path=QPainterPath();path.addPolygon(QPolygonF([s0,s1,s2]));path.closeSubpath()
                stroke=QPainterPathStroker();stroke.setWidth(.7)
                painter.setClipPath(path.united(stroke.createStroke(path)),Qt.ClipOperation.IntersectClip)
                src_left=max(0,math.floor(sx)-2);src_top=max(0,math.floor(sy)-2);src_right=min(sw,math.ceil(sx+ew)+2);src_bottom=min(sh,math.ceil(sy+eh)+2)
                region=QRectF(src_left,src_top,src_right-src_left,src_bottom-src_top)
                painter.drawImage(region,image,region);painter.restore()
    painter.end()
    original.drawImage(QRectF(left,top,output.width(),output.height()),output)
