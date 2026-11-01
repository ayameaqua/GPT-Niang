"""Continuous weights along the painted tail, including a returning U bend.

Euclidean nearest-bone weights jump between neighbouring limbs of a U. An
authored centreline seeds a harmonic coordinate inside the alpha silhouette.
"""
from bisect import bisect_right
from collections import deque
import heapq
import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage


class TailSkin:
    def __init__(self,image,nodes,resolution=128):
        scale=min(1.,resolution/max(image.width(),image.height()))
        self.width=max(2,round(image.width()*scale));self.height=max(2,round(image.height()*scale))
        small=image.scaled(self.width,self.height,Qt.AspectRatioMode.IgnoreAspectRatio,
                           Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_RGBA8888)
        alpha=bytes(small.constBits())[3::4];count=len(alpha)
        occupied=[a>=48 for a in alpha]
        def index(uv):
            x=max(0,min(self.width-1,round(uv[0]*(self.width-1))))
            y=max(0,min(self.height-1,round(uv[1]*(self.height-1))))
            if occupied[y*self.width+x]:return y*self.width+x
            return min((i for i in range(count) if occupied[i]),
                       key=lambda i:(i%self.width-x)**2+(i//self.width-y)**2)
        points=[(u*(self.width-1),v*(self.height-1)) for u,v in nodes]
        self.knots=[0.]
        for a,b in zip(points,points[1:]):self.knots.append(self.knots[-1]+math.dist(a,b))
        distance=[math.inf]*count;parameter=[0.]*count;fixed=set();queue=[]
        for bone,(a,b) in enumerate(zip(points,points[1:])):
            steps=max(1,math.ceil(math.dist(a,b)*2))
            for step in range(steps+1):
                t=step/steps;x=round(a[0]+(b[0]-a[0])*t);y=round(a[1]+(b[1]-a[1])*t);i=y*self.width+x
                if not occupied[i]:continue
                parameter[i]=self.knots[bone]+(self.knots[bone+1]-self.knots[bone])*t
                if i not in fixed:fixed.add(i);distance[i]=0.;heapq.heappush(queue,(0.,i))
        neighbours=((-1,-1,math.sqrt(2)),(0,-1,1),(1,-1,math.sqrt(2)),(-1,0,1),
                    (1,0,1),(-1,1,math.sqrt(2)),(0,1,1),(1,1,math.sqrt(2)))
        while queue:
            value,i=heapq.heappop(queue)
            if value!=distance[i]:continue
            x,y=i%self.width,i//self.width
            for dx,dy,cost in neighbours:
                xx,yy=x+dx,y+dy
                if not (0<=xx<self.width and 0<=yy<self.height):continue
                j=yy*self.width+xx
                if occupied[j] and value+cost<distance[j]:
                    distance[j]=value+cost;parameter[j]=parameter[i];heapq.heappush(queue,(distance[j],j))
        interior=[]
        for i in range(count):
            if not occupied[i] or not math.isfinite(distance[i]) or i in fixed:continue
            x,y=i%self.width,i//self.width
            adjacent=[(y+dy)*self.width+x+dx for dx,dy,_ in neighbours
                      if 0<=x+dx<self.width and 0<=y+dy<self.height and occupied[(y+dy)*self.width+x+dx]]
            if adjacent:interior.append((i,adjacent))
        for _ in range(24):
            for i,adjacent in interior:parameter[i]=sum(parameter[j] for j in adjacent)/len(adjacent)
        # Extend into transparent margins so a mesh vertex outside the texture
        # has a useful weight. This does not connect tissue across the gap.
        frontier=deque(i for i,d in enumerate(distance) if math.isfinite(d))
        if not frontier:raise ValueError('无有效尾部蒙皮区域')
        known=[math.isfinite(d) for d in distance]
        while frontier:
            i=frontier.popleft();x,y=i%self.width,i//self.width
            for dx,dy,_ in neighbours:
                xx,yy=x+dx,y+dy
                if not (0<=xx<self.width and 0<=yy<self.height):continue
                j=yy*self.width+xx
                if not known[j]:known[j]=True;parameter[j]=parameter[i];frontier.append(j)
        self.distance=parameter
        boundary=[]
        for i in range(count):
            if not occupied[i]:continue
            x,y=i%self.width,i//self.width
            if any(not (0<=x+dx<self.width and 0<=y+dy<self.height) or not occupied[(y+dy)*self.width+x+dx] for dx,dy,_ in neighbours):
                boundary.append((x/(self.width-1),y/(self.height-1)))
        stride=max(1,len(boundary)//256)
        self.boundary=[(u,v,self.weights(u,v)) for u,v in boundary[::stride]]

    def at(self,u,v):
        x=max(0.,min(self.width-1.,u*(self.width-1)))
        y=max(0.,min(self.height-1.,v*(self.height-1)))
        x0,y0=int(x),int(y);x1=min(x0+1,self.width-1);y1=min(y0+1,self.height-1)
        tx,ty=x-x0,y-y0;d=self.distance;w=self.width
        a=d[y0*w+x0]*(1-tx)+d[y0*w+x1]*tx
        b=d[y1*w+x0]*(1-tx)+d[y1*w+x1]*tx
        return a*(1-ty)+b*ty

    def weights(self,u,v):
        value=self.at(u,v);count=len(self.knots)-1
        i=max(0,min(count-1,bisect_right(self.knots,value)-1))
        weights=[0.]*count;weights[i]=1.
        def smooth(x):
            x=max(0.,min(1.,x));return x*x*(3-2*x)
        # Blend across each anatomical joint, with no nearest-bone ownership
        # boundary through the middle of the thick shaft or the leaf.
        for joint in (i,i+1):
            if not 0<joint<count:continue
            width=max(1.5,min(self.knots[joint]-self.knots[joint-1],self.knots[joint+1]-self.knots[joint])*.10)
            if abs(value-self.knots[joint])<=width:
                amount=smooth((value-self.knots[joint]+width)/(2*width))
                weights=[0.]*count;weights[joint-1]=1-amount;weights[joint]=amount;break
        return weights
