"""Independent head surfaces and appendages, registered to one neck joint.

Hair and skin have separate windows. A rear texture never stretches into a
cheek, and eyes retain anatomical identity when the visible side changes.
Original appendage pixels are read only from the user's imported model.
"""
from collections import deque
from bisect import bisect_left
from dataclasses import replace
import json
import math

from PySide6.QtCore import QPointF,QRectF,Qt
from PySide6.QtGui import QImage,QPainter,QPainterPath,QPolygonF,QTransform

from .kinematics import VIEW_ANGLES,head_point
from .motion import smooth
from .silhouette import RasterPalette,SilhouetteWarp,draw_quad,mip_texture

NECK=(425.,460.)


def lerp(a,b,t):return a+(b-a)*t


def ear_back_material(front,back):
    """UV-register outer-ear colour onto the imported ear's exact alpha.

    This is a runtime material lookup, not a second independently sized leaf.
    Neither imported pixels nor generated art are written back to disk.
    """
    def axis(part):
        image,root,tip=part;w,h=image.width(),image.height()
        root=(root[0]*w,root[1]*h);tip=(tip[0]*w,tip[1]*h)
        length=math.dist(root,tip);d=((tip[0]-root[0])/length,(tip[1]-root[1])/length);n=(-d[1],d[0])
        def local(x,y):return (x-root[0])*n[0]+(y-root[1])*n[1],(x-root[0])*d[0]+(y-root[1])*d[1]
        corners=[local(x,y) for x,y in ((0,0),(w,0),(w,h),(0,h))]
        left=math.floor(min(p[0] for p in corners))-2;top=math.floor(min(p[1] for p in corners))-2
        width=math.ceil(max(p[0] for p in corners))-left+2;height=math.ceil(max(p[1] for p in corners))-top+2
        output=QImage(width,height,QImage.Format.Format_ARGB32_Premultiplied);output.fill(Qt.GlobalColor.transparent)
        painter=QPainter(output);painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setTransform(QTransform(n[0],d[0],n[1],d[1],-root[0]*n[0]-root[1]*n[1]-left,-root[0]*d[0]-root[1]*d[1]-top))
        painter.drawImage(0,0,image);painter.end()
        output=output.convertToFormat(QImage.Format.Format_RGBA8888);rgba=bytes(output.constBits());alpha=rgba[3::4]
        rows=[]
        for y in range(height):
            line=alpha[y*width:(y+1)*width].translate(bytes(1 if a>=32 else 0 for a in range(256)))
            a,b=line.find(b'\1'),line.rfind(b'\1');rows.append((a,b) if a>=0 else None)
        previous=next(row for row in rows if row)
        valid=[i for i,row in enumerate(rows) if row]
        nearest=[]
        for i in range(height):
            j=bisect_left(valid,i);choices=valid[max(0,j-1):min(len(valid),j+1)]
            nearest.append(min(choices,key=lambda value:abs(i-value)))
        for i,row in enumerate(rows):previous=row or previous;rows[i]=previous
        return output,rgba,rows,local,(-left,-top),length,nearest
    target,tdata,trows,local,troot,tlength,_=axis(front)
    source,sdata,srows,_,sroot,slength,nearest=axis(back);sw,sh=source.width(),source.height()
    image=front[0].convertToFormat(QImage.Format.Format_RGBA8888);w,h=image.width(),image.height();data=bytearray(image.constBits())
    for y in range(h):
        for x in range(w):
            index=(y*w+x)*4
            if not data[index+3]:continue
            q,s=local(x+.5,y+.5);row=max(0,min(len(trows)-1,round(s+troot[1])));left,right=trows[row]
            fraction=max(.01,min(.99,(q+troot[0]-left)/max(1,right-left)))
            yy=nearest[max(0,min(sh-1,round(sroot[1]+s/tlength*slength)))];a,b=srows[yy]
            xx=max(0,min(sw-1,round(lerp(a,b,fraction))));other=(yy*sw+xx)*4
            if sdata[other+3]<32:
                candidates=[j for j in range(a,b+1) if sdata[(yy*sw+j)*4+3]>=32]
                if not candidates:continue
                xx=min(candidates,key=lambda value:abs(value-xx));other=(yy*sw+xx)*4
            data[index:index+3]=sdata[other:other+3]
    return QImage(bytes(data),w,h,w*4,QImage.Format.Format_RGBA8888).copy()


class HeadFrame:
    def __init__(self,renderer,spec):
        crop=spec['runtimeCrop'];image=QImage(str(renderer.extension_directory/spec['src'])).copy(*crop['sourceRectPx'])
        dx,dy=425-spec['neck'][0],460-spec['neck'][1]
        self.box=[*crop['box']];self.box[0]+=dx;self.box[1]+=dy
        self.neck_regions=spec.get('neckMaskRegions',[])
        self.face=spec['face'];self.sides=spec['featureAnatomicalSides'];self.features={};self.feature_specs={};self.decor={}
        if self.face:
            for name in self.face.get('features',{}):
                x,y,w,h=renderer._face_feature_rect(self.face,name)
                self.features[name]=[x+dx,y+dy,w,h]
                part=self.face['features'][name]
                self.feature_specs[name]={**part,'flipX':bool(part.get('flipX'))^bool(self.face.get('flip'))}
            fx,fy,fw,fh=self.face['box']
            for kind in ('blush','tears'):
                for index,side in enumerate(('far','near')):
                    value=self.face.get(kind,[[-100,-100],[-100,-100]])[index]
                    if value[0]<-50:continue
                    xx,yy=value[:2];ww,hh=value[2:] if kind=='blush' else (0,0)
                    if self.face.get('flip'):xx=230-xx-ww
                    self.decor[kind,self.sides[side]]=[fx+xx/230*fw+dx,fy+yy/150*fh+dy,ww/230*fw,hh/150*fh]
        crown=spec['headCrown'][0]+dx
        self.palette=RasterPalette(image,self.box,NECK,crown)
        self.image=self.palette.image;self.box=self.palette.box
        self.skin=self._skin_rows()
        self.closed=[]
        valid=[i for i,row in enumerate(self.skin) if row]
        for i in range(len(self.skin)):
            if not valid:self.closed.append((NECK[0],NECK[0]));continue
            j=bisect_left(valid,i);lo=valid[max(0,j-1)];hi=valid[min(len(valid)-1,j)]
            a,b=self.skin[lo],self.skin[hi];amount=(i-lo)/max(1,hi-lo)
            self.closed.append((lerp((a[0]+a[1])/2,(b[0]+b[1])/2,amount),lerp((a[2]+a[3])/2,(b[2]+b[3])/2,amount)))

    def _skin_rows(self):
        image=self.image.scaledToWidth(420,Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_RGBA8888)
        w,h=image.width(),image.height();pixels=bytes(image.constBits());x,y,bw,bh=self.box
        eligible=bytearray(w*h)
        for i in range(w*h):
            r,g,b,a=pixels[i*4:i*4+4]
            if a>=32 and r>=175 and g>=110 and b>=110 and r>=b+2 and r>=g+1:eligible[i]=1
        visited=bytearray(w*h);rows=[]
        if self.face:
            mouth=self.features['mouth'];mx,my=mouth[0]+mouth[2]/2,mouth[1]-8
            sx=max(0,min(w-1,round((mx-x)/bw*w)));sy=max(0,min(h-1,round((my-y)/bh*h)))
            seeds=[yy*w+xx for yy in range(max(0,sy-20),min(h,sy+21)) for xx in range(max(0,sx-20),min(w,sx+21)) if eligible[yy*w+xx]]
            if seeds:
                seed=min(seeds,key=lambda i:(i%w-sx)**2+(i//w-sy)**2);visited[seed]=1;queue=deque([seed])
                while queue:
                    i=queue.popleft();xx=i%w
                    for other in (i-1 if xx else -1,i+1 if xx<w-1 else -1,i-w,i+w):
                        if 0<=other<w*h and eligible[other] and not visited[other]:visited[other]=1;queue.append(other)
                middle=(mx-x)/bw*w
                for yy in range(h):
                    if y+yy/h*bh>468:rows.append(None);continue
                    left=[xx for xx in range(w) if visited[yy*w+xx] and xx<=middle]
                    right=[xx for xx in range(w) if visited[yy*w+xx] and xx>middle]
                    if not left and not right:rows.append(None);continue
                    aa=(min(left),max(left)+1) if left else (middle,middle)
                    bb=(min(right),max(right)+1) if right else (middle,middle)
                    rows.append(tuple(x+value/w*bw for value in (*aa,*bb)))
        # Neck belongs to the body, including isolated baked neck islands in
        # no-face rear cores. Mouth flood alone cannot find those islands.
        mask=bytearray(b'\xff'*(w*h*4));islands=[]
        for index in range(w*h):
            if visited[index] and y+(index//w)/h*bh>468:mask[index*4+3]=0
        # Explicitly measured ROIs select the actual neck components. Sparse
        # warm highlights in white hair must never become expanded holes.
        for rx,ry,rw,rh in self.neck_regions:
            seen=set();components=[]
            for index in range(w*h):
                xx,yy=index%w,index//w;wx,wy=x+xx/w*bw,y+yy/h*bh
                if index in seen or visited[index] or not eligible[index] or not (rx<=wx<=rx+rw and ry<=wy<=ry+rh):continue
                queue=deque([index]);seen.add(index);component=[]
                while queue:
                    current=queue.popleft();component.append(current);cx=current%w
                    for other in (current-1 if cx else -1,current+1 if cx<w-1 else -1,current-w,current+w):
                        if 0<=other<w*h and other not in seen and eligible[other] and not visited[other]:seen.add(other);queue.append(other)
                xs=[x+(value%w)/w*bw for value in component];ys=[y+(value//w)/h*bh for value in component]
                if min(xs)>=rx and max(xs)<=rx+rw and min(ys)>=ry and max(ys)<=ry+rh:components.append(component)
            component=max(components,key=len,default=[])
            if len(component)>=32:
                for index in component:mask[index*4+3]=0;islands.append((index%w,index//w))
        # Include the ink outline of isolated baked necks. Removing only their
        # warm interior leaves a detached purple line in the profile view.
        halo=set()
        for xx,yy in islands:
            for dy in range(-3,4):
                for dx in range(-3,4):
                    px,py=xx+dx,yy+dy
                    if dx*dx+dy*dy<=9 and 0<=px<w and 0<=py<h:halo.add(py*w+px)
        for index in halo:
            if not mask[index*4+3]:continue
            xx,yy=index%w,index//w
            # A neck/hair shared boundary is real hair ink. Expand only toward
            # the original transparent exterior, never across opaque hair.
            if any(pixels[(py*w+px)*4+3]<32
                   for py in range(max(0,yy-3),min(h,yy+4))
                   for px in range(max(0,xx-3),min(w,xx+4))
                   if (px-xx)**2+(py-yy)**2<=9):mask[index*4+3]=0
        alpha=QImage(bytes(mask),w,h,w*4,QImage.Format.Format_RGBA8888).copy().scaled(self.image.size(),Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation)
        painter=QPainter(self.image);painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn);painter.drawImage(0,0,alpha);painter.end()
        return rows

    def row(self,y):
        left,centre,right=self.palette.bounds(y)
        if self.skin:
            position=max(0,min(len(self.skin)-1,round((y-self.box[1])/self.box[3]*(len(self.skin)-1))))
            skin=self.skin[position]
            if skin:
                values=[max(left,min(right,value)) for value in skin]
                values=sorted(values)
                return (left,*values,right),True
            a,b=self.closed[position]
            a=max(left,min(right,a));b=max(a,min(right,b))
            return (left,a,a,b,b,right),False
        return (left,centre,centre,centre,centre,right),False


class LayeredHead:
    def __init__(self,renderer):
        self.renderer=renderer
        self.spec=json.loads((renderer.extension_directory/'head.json').read_text())
        self.frames={};self.parts={};self.rejected=0;self.hair_cache={}
        self.choices={name:frame['angle'] for name,frame in self.spec['cores'].items()}
        for name,part in self.spec['parts'].items():
            source=renderer.images[part['asset'].split('/')[-1].split('.')[0]]
            u,v,w,h=part['sourceRectUV'];rect=[round(u*source.width()),round(v*source.height()),round(w*source.width()),round(h*source.height())]
            self.parts[name]=(source.copy(*rect),part['rootCropUV'],part['tipCropUV'])
        for key in ('earBack','hairpin'):
            part=self.spec[key];self.parts[key]=(QImage(str(renderer.extension_directory/part['src'])),part['rootUV'],part['tipUV'])
        for name in ('earLeft','earRight'):
            front=self.parts[name];self.parts[name+'Back']=(ear_back_material(front,self.parts['earBack']),front[1],front[2])
        self.parts['ahoge']=(renderer.images['ahoge'],[(399-363)/87,(165-70)/97],[(447-363)/87,(95-70)/97])

    def frame(self,name):
        if name not in self.frames:self.frames[name]=HeadFrame(self.renderer,self.spec['cores'][name])
        return self.frames[name]

    def path(self,angle,name,field):
        a,b,t=self.renderer._neighbors(angle)
        # Periodic Catmull-Rom keeps velocity continuous at all native views.
        ordered=list(VIEW_ANGLES);index=ordered.index(a)
        names=(ordered[(index-1)%8],a,b,ordered[(index+2)%8])
        points=[self.spec['paths'][key]['appendages'][name][field] for key in names]
        return tuple(NECK[i]+.5*((2*points[1][i])+(-points[0][i]+points[2][i])*t+(2*points[0][i]-5*points[1][i]+4*points[2][i]-points[3][i])*t*t+(-points[0][i]+3*points[1][i]-3*points[2][i]+points[3][i])*t*t*t) for i in (0,1))

    @staticmethod
    def paired_rows(first,second,y,second_y=None):
        a,has_a=first.row(y);b,has_b=second.row(y if second_y is None else second_y)
        if first.face is None and second.face:
            mouth=second.features['mouth'];edge=a[0] if mouth[0]+mouth[2]/2<NECK[0] else a[5]
            a=(a[0],edge,edge,edge,edge,a[5])
        if first.face and second.face is None:
            mouth=first.features['mouth'];edge=b[0] if mouth[0]+mouth[2]/2<NECK[0] else b[5]
            b=(b[0],edge,edge,edge,edge,b[5])
        return a,b

    @classmethod
    def common_row(cls,first,second,t,y):
        a,b,_,_=cls.sample_rows(first,second,t,y)
        return tuple(lerp(x,z,t) for x,z in zip(a,b))

    @classmethod
    def sample_rows(cls,first,second,t,y):
        ys=tuple(lerp(a,b,t) for a,b in zip(first.palette.ys,second.palette.ys))
        i,phase=SilhouetteWarp.phase(y,ys)
        ay=lerp(first.palette.ys[i],first.palette.ys[i+1],phase)
        by=lerp(second.palette.ys[i],second.palette.ys[i+1],phase)
        a,b=cls.paired_rows(first,second,ay,by)
        return a,b,ay,by

    def _hair(self,painter,first,second,t,project,zones=(0,2,4),source_index=None):
        preferred=first if (t<.5 if source_index is None else source_index==0) else second
        alternate=second if preferred is first else first
        top=lerp(first.palette.ys[0],second.palette.ys[0],t);bottom=lerp(first.palette.ys[-1],second.palette.ys[-1],t)
        rows=100;step=(bottom-top)/rows
        for row in range(rows):
            y0=top+step*row;y1=y0+step
            common=[self.common_row(first,second,t,y) for y in (y0,y1)]
            samples=[self.sample_rows(first,second,t,y) for y in (y0,y1)]
            for zone in zones:
                if max(edge[zone+1]-edge[zone] for edge in common)<.02:continue
                source=preferred
                sr=[sample[0 if source is first else 1] for sample in samples]
                if min(edge[zone+1]-edge[zone] for edge in sr)<.01:
                    source=alternate;sr=[sample[0 if source is first else 1] for sample in samples]
                if max(edge[zone+1]-edge[zone] for edge in sr)<.01:continue
                texture=mip_texture(painter,source.image,*source.box[2:]);x,y,w,h=source.box
                yy=[sample[2 if source is first else 3] for sample in samples]
                source_points=[(sr[0][zone],yy[0]),(sr[0][zone+1],yy[0]),(sr[1][zone+1],yy[1]),(sr[1][zone],yy[1])]
                uv=[((xx-x)/w*texture.width(),(yy-y)/h*texture.height()) for xx,yy in source_points]
                target=[project((common[0][zone],y0)),project((common[0][zone+1],y0)),project((common[1][zone+1],y1)),project((common[1][zone],y1))]
                self.rejected+=not draw_quad(painter,texture,uv,target)

    def _skin_clip(self,first,second,t,project):
        path=QPainterPath();top=lerp(first.palette.ys[0],second.palette.ys[0],t);bottom=469.;step=3.
        y=top
        while y<bottom:
            y1=min(bottom,y+step);a=self.common_row(first,second,t,y);b=self.common_row(first,second,t,y1)
            for left,right in ((1,2),(3,4)):
                points=[project((a[left],y)),project((a[right],y)),project((b[right],y1)),project((b[left],y1))]
                if max(a[right]-a[left],b[right]-b[left])>.02:
                    path.addPolygon(QPolygonF([QPointF(*point) for point in points]));path.closeSubpath()
            y=y1
        return path.simplified()

    def _layout(self,first,second,t):
        features={};opacities=[];box=[235.,245.,380.,225.]
        def feature(frame,anatomy,kind):
            if not frame.face:return None,None
            side=next((side for side,value in frame.sides.items() if value==anatomy),None)
            key=f'brow-{side}' if kind=='brow' else f'eye-{side}-{kind}'
            return frame.features.get(key),frame.feature_specs.get(key)
        for target,anatomy in (('far','right'),('near','left')):
            present=[]
            for kind in ('white','iris','lash','brow'):
                a,sa=feature(first,anatomy,kind);b,sb=feature(second,anatomy,kind)
                present=[bool(a),bool(b)]
                if a is None and b is None:continue
                if a is None:a=[b[0]+b[2]/2,b[1],0,b[3]]
                if b is None:b=[a[0]+a[2]/2,a[1],0,a[3]]
                rect=[lerp(x,y,t) for x,y in zip(a,b)];source=sa if t<.5 and sa else sb or sa
                name=f'brow-{target}' if kind=='brow' else f'eye-{target}-{kind}'
                features[name]={**source,'box':[(rect[0]-box[0])/box[2]*230,(rect[1]-box[1])/box[3]*150,rect[2]/box[2]*230,rect[3]/box[3]*150]}
            opacities.append(lerp(*present,t))
        a=first.features.get('mouth');b=second.features.get('mouth')
        if a or b:
            if a is None:a=b
            if b is None:b=a
            x,y,w,h=[lerp(x,y,t) for x,y in zip(a,b)]
            features['mouth']={'source':'mouth','box':[(x-box[0])/box[2]*230,(y-box[1])/box[3]*150,w/box[2]*230,h/box[3]*150]}
        else:features['mouth']={'box':[-100,-100,1,1]}
        # Missing features must stay hidden rather than falling back to the
        # upstream atlas at a different location.
        for side in ('far','near'):
            for kind in ('white','iris','lash'):
                features.setdefault(f'eye-{side}-{kind}',{'box':[-100,-100,0,0]})
            features.setdefault(f'brow-{side}',{'box':[-100,-100,0,0]})
        decor={kind:[] for kind in ('blush','tears')}
        for kind in decor:
            for anatomy in ('right','left'):
                a=first.decor.get((kind,anatomy));b=second.decor.get((kind,anatomy))
                if a is None and b is None:rect=[-100,-100,0,0]
                else:
                    if a is None:a=[b[0]+b[2]/2,b[1],0,b[3]]
                    if b is None:b=[a[0]+a[2]/2,a[1],0,a[3]]
                    x,y,w,h=[lerp(x,y,t) for x,y in zip(a,b)]
                    rect=[(x-box[0])/box[2]*230,(y-box[1])/box[3]*150,w/box[2]*230,h/box[3]*150]
                decor[kind].append(rect if kind=='blush' else rect[:2])
        return {'box':box,'features':features,'eyeOpacity':opacities,'winkEye':int(opacities[1]>opacities[0]),**decor}

    def _skin(self,painter,first,second,t,project):
        self._hair(painter,first,second,t,project,zones=(1,3))

    def _part(self,painter,name,root,tip,project,width=1.,texture=None):
        if width<1e-5:return
        image,root_uv,tip_uv=self.parts[name];image=image if texture is None else texture;w,h=image.width(),image.height()
        sx,sy=root_uv[0]*w,root_uv[1]*h;ex,ey=tip_uv[0]*w,tip_uv[1]*h
        root=project(root);tip=project(tip);vx,vy=ex-sx,ey-sy;length=math.hypot(vx,vy)
        dx,dy=tip[0]-root[0],tip[1]-root[1];scale=math.hypot(dx,dy)/length
        angle=math.atan2(dy,dx)-math.atan2(vy,vx);c,s=math.cos(angle),math.sin(angle)
        # Width is measured perpendicular to the ear's own root-tip axis.
        ux,uy=vx/length,vy/length
        a=ux*ux+uy*uy*width;b=ux*uy*(1-width);d=uy*uy+ux*ux*width
        m11=scale*(c*a-s*b);m12=scale*(s*a+c*b);m21=scale*(c*b-s*d);m22=scale*(s*b+c*d)
        transform=QTransform(m11,m12,m21,m22,root[0]-m11*sx-m21*sy,root[1]-m12*sx-m22*sy)
        painter.save();painter.setTransform(transform,True);painter.drawImage(0,0,image);painter.restore()

    def draw(self,painter,pose,angle,target_neck):
        # Keep complete native hair/skin material together. The rejected
        # intermediate surface stretched curls and separated the fringe.
        native=min(self.choices,key=lambda name:abs((self.choices[name]-angle+180)%360-180))
        angle=self.choices[native];first=second=self.frame(native);t=0.
        pa,pb,pt=self.renderer._neighbors(angle)
        def project(point):
            a=head_point(point,NECK,[190,65,470,475],pose.head_pitch,pose.head_yaw,pa)
            b=head_point(point,NECK,[190,65,470,475],pose.head_pitch,pose.head_yaw,pb)
            return tuple(lerp(x,y,pt) for x,y in zip(a,b))
        neutral=lambda point:point
        material=self.hair_cache.get(angle)
        if material is None:
            clip=self._skin_clip(first,second,t,neutral)
            hair=QImage(700,620,QImage.Format.Format_ARGB32_Premultiplied);hair.fill(Qt.GlobalColor.transparent)
            hp=QPainter(hair);hp.setRenderHints(painter.renderHints());hp.translate(-100,-40)
            hp.drawImage(QRectF(*first.box),first.image);hp.end()
            skin=QImage(hair.size(),hair.format());skin.fill(Qt.GlobalColor.transparent)
            material=hair,skin,clip,self._layout(first,first,0),None
            if len(self.hair_cache)>=16:del self.hair_cache[next(iter(self.hair_cache))]
            self.hair_cache[angle]=material
        hair,skin,clip,layout,foreground=material
        painter.save();pivots={**self.renderer.pivots,**self.renderer.rigs.get(pose.view,({},{}))[0].get('pivots',{})}
        self.renderer._joint(painter,'upper',pose,pivots)
        painter.translate(target_neck[0]-425,target_neck[1]-460)
        self.renderer._joint(painter,'head',replace(pose,transforms={**pose.transforms,'upper':{}}),{'head':NECK,'upper':NECK})
        def appendage(name,target):
            root=self.path(angle,name,'attachmentOffset');tip=self.path(angle,name,'tipOffset')
            if name.startswith('ear'):
                facing=math.cos(math.radians(angle-(45 if name.endswith('Left') else -45)))
                a,b,phase=self.renderer._neighbors(angle)
                lengths=[]
                for view in (a,b):
                    spec=self.spec['paths'][view]['appendages'][name]
                    lengths.append(math.dist(spec['attachmentOffset'],spec['tipOffset']))
                # The projected long axis may foreshorten. Preserve the other
                # plane basis instead of shrinking the whole ear a second time.
                width=lerp(*lengths,phase)/max(.01,math.dist(root,tip))
                back=smooth((.15-facing)/.30)
                texture=self.renderer._mix(self.parts[name][0],self.parts[name+'Back'][0],back)
                self._part(target,name,root,tip,project,width,texture)
            else:self._part(target,name,root,tip,project)
        self._part(painter,'ahoge',self.path(angle,'ahoge','attachmentOffset'),self.path(angle,'ahoge','tipOffset'),project)
        pin_facing=math.cos(math.radians(angle-45))
        def pin():
            self._part(painter,'hairpin',self.path(angle,'hairpin','attachmentOffset'),self.path(angle,'hairpin','tipOffset'),project,abs(pin_facing))
        if pin_facing<0:pin()
        surface=hair.copy()
        sp=QPainter(surface);sp.setRenderHints(painter.renderHints());sp.translate(-100,-40)
        if foreground is not None:
            sp.drawImage(QPointF(100,40),foreground);sp.drawImage(QPointF(100,40),skin)
        sp.save();sp.setClipPath(clip,Qt.ClipOperation.IntersectClip)
        from .raster_mesh import draw_mesh
        for lashes in (False,True):
            image=self.renderer._face(pose,lashes,False,layout)
            sp.drawImage(QRectF(*layout['box']),image)
        sp.restore()
        sp.end()
        if abs(pose.head_pitch)+abs(pose.head_yaw)>.0001:
            projected=QImage(700,620,QImage.Format.Format_ARGB32_Premultiplied);projected.fill(Qt.GlobalColor.transparent)
            hp=QPainter(projected);hp.setRenderHints(painter.renderHints());hp.translate(-100,-40)
            draw_mesh(hp,surface,[100,40,700,620],project,columns=12,rows=16);hp.end();surface=projected
        painter.drawImage(QPointF(100,40),surface)
        for name in ('hornLeft','hornRight','earLeft','earRight'):
            layer=QImage(700,620,QImage.Format.Format_ARGB32_Premultiplied);layer.fill(Qt.GlobalColor.transparent)
            lp=QPainter(layer);lp.setRenderHints(painter.renderHints());lp.translate(-100,-40);appendage(name,lp)
            depth=math.sin(math.radians(angle))*(1 if name.endswith('Left') else -1)
            hidden=smooth(-depth/.24)
            lp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut);lp.setOpacity(hidden)
            lp.drawImage(QPointF(100,40),surface);lp.end();painter.drawImage(QPointF(100,40),layer)
        # Near roots are buried by the same scalp material, without redrawing
        # the whole head over the appendage.
        for name in ('hornLeft','hornRight','earLeft','earRight'):
            root=project(self.path(angle,name,'attachmentOffset'));painter.save()
            path=QPainterPath();path.addEllipse(QRectF(root[0]-19,root[1]-12,38,26))
            painter.setClipPath(path,Qt.ClipOperation.IntersectClip);painter.drawImage(QPointF(100,40),surface);painter.restore()
        if pin_facing>=0:pin()
        painter.restore()
