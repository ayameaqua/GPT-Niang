"""Extract explicitly selected sprite islands; never infer a binding from a grid.

Only copies original RGBA samples. A two-pixel neighborhood retains antialiased
edges; unrelated opaque components inside an overlapping bounding box are not
copied. Detached legitimate details must be named by an explicit include box.
"""
from array import array
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QImage


@dataclass
class Component:
    label: int
    area: int
    bounds: tuple  # half-open x0,y0,x1,y1


def intersection(a, b):
    return max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))


class Atlas:
    def __init__(self, source):
        self.source = str(source)
        self.image = QImage(str(source)).convertToFormat(QImage.Format.Format_RGBA8888)
        if self.image.isNull():
            raise ValueError(f"Invalid atlas: {source}")
        self.width, self.height = self.image.width(), self.image.height()
        if max(self.width,self.height)>4096:
            raise ValueError("Atlas exceeds source-size limit")
        self.rgba = bytes(self.image.constBits())
        self.alpha = self.rgba[3::4]
        self.labels = array('i', [0])*(self.width*self.height)
        self.components = []
        w,h = self.width,self.height
        for pixel, alpha in enumerate(self.alpha):
            if alpha < 128 or self.labels[pixel]:
                continue
            label = len(self.components)+1
            todo = deque([pixel]); self.labels[pixel]=label
            count=0; x0=w; y0=h; x1=y1=0
            while todo:
                p=todo.popleft(); y,x=divmod(p,w)
                count+=1; x0=min(x0,x);x1=max(x1,x+1);y0=min(y0,y);y1=max(y1,y+1)
                neighbors=[]
                if x: neighbors.append(p-1)
                if x+1<w: neighbors.append(p+1)
                if y: neighbors.append(p-w)
                if y+1<h: neighbors.append(p+w)
                for n in neighbors:
                    if self.alpha[n]>=128 and not self.labels[n]:
                        self.labels[n]=label;todo.append(n)
            self.components.append(Component(label,count,(x0,y0,x1,y1)))

    def choose(self, locator):
        """Locator identifies the subject, but never clips its actual silhouette."""
        x,y,w,h=locator; bounds=(x,y,x+w,y+h)
        candidates=[c for c in self.components if c.area>=16 and intersection(c.bounds,bounds)]
        if not candidates:
            raise ValueError(f"No component near {locator}: {self.source}")
        def score(c):
            x0,y0,x1,y1=c.bounds
            return c.area*intersection(c.bounds,bounds)/((x1-x0)*(y1-y0))
        return max(candidates,key=score)

    def extract(self, locator, include=(), padding=2):
        selected=[self.choose(locator)]+[self.choose(box) for box in include]
        ids={c.label for c in selected}
        x0=max(0,min(c.bounds[0] for c in selected)-padding)
        y0=max(0,min(c.bounds[1] for c in selected)-padding)
        x1=min(self.width,max(c.bounds[2] for c in selected)+padding)
        y1=min(self.height,max(c.bounds[3] for c in selected)+padding)
        w,h=x1-x0,y1-y0
        mask=bytearray(w*h)
        # Dilate runs, not the whole image, to keep antialias samples adjacent to
        # selected contours without letting alpha=1 noise connect all atlas cells.
        for y in range(h):
            x=0
            while x<w:
                if self.labels[(y+y0)*self.width+x+x0] not in ids:
                    x+=1;continue
                start=x
                while x<w and self.labels[(y+y0)*self.width+x+x0] in ids:x+=1
                lo=max(0,start-padding); hi=min(w,x+padding)
                for yy in range(max(0,y-padding),min(h,y+padding+1)):
                    mask[yy*w+lo:yy*w+hi]=b'\1'*(hi-lo)
        pixels=bytearray(w*h*4)
        for y in range(h):
            for x in range(w):
                src=(y+y0)*self.width+x+x0
                label=self.labels[src]
                if mask[y*w+x] and (label==0 or label in ids):
                    pixels[(y*w+x)*4:(y*w+x+1)*4]=self.rgba[src*4:src*4+4]
        image=QImage(pixels,w,h,w*4,QImage.Format.Format_RGBA8888).copy()
        return image, {'source':self.source,'locator':locator,'include':list(include),
                       'sourceBounds':[x0,y0,x1,y1], 'selectedComponents':[
                           {'area':c.area,'bounds':list(c.bounds)} for c in selected],
                       'edgePadding':padding,'outputSize':[w,h]}
