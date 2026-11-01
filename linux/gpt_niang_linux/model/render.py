"""Qt raster compositor with hierarchical joints, skeletal motion and native direction frames.

Renders on the GUI thread to an immutable image shared with Quick. The same
composite supplies the input mask, so a raised arm cannot leave a stale hit box.
No native plugin/Qt private ABI or browser runtime is required.
"""
import json
import math
import logging
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBitmap,QColor,QImage,QLinearGradient,QPainter,QPainterPath,QPen,QPolygonF,QRegion,QTransform

from .assets import validate_model
from .motion import HAND_GESTURES, smooth
from .articulation import arm_chain
from .kinematics import VIEW_ANGLES,head_point,solve_leg,skin_point,rotate,coccyx_point
from .raster_mesh import draw_mesh
from .skinning import TailSkin
from ..paths import LINUX_ROOT

PARENTS = {"head": "upper", "hairBack": "head", "hairFront": "head", "ahoge": "head",
           "wingFar": "upper", "wingNear": "upper", "armFar": "upper", "armNear": "upper"}
DESIGN_SIZE = 1280
INK = QColor("#574258")


class DragonRenderer:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.model = validate_model(json.loads((self.directory / "model.json").read_text()))
        self.parts = {p["id"]: p for p in self.model["parts"]}
        self.images = {key: QImage(str(self.directory / part["src"])) for key, part in self.parts.items()}
        if any(image.isNull() or max(image.width(), image.height()) > 2048 for image in self.images.values()):
            raise ValueError("缺失或无效的角色图片")
        self.pivots = {**self.model["pivots"], "seat": [425, 570], "hairBack": [450, 245], "hairFront": [407, 248]}
        self.rigs = {}
        self.view_errors = []
        self.warp_cache = {}
        self.texture_cache = {}
        self.face_masks = {}
        self.tail_skins={}
        self.extension_directory = LINUX_ROOT / "models/dragon"
        self.puppet={};self.puppet_images={}
        self.head_frames={}
        puppet=self.extension_directory/'puppet.json'
        if puppet.exists():
            self.puppet=json.loads(puppet.read_text())
            textures={f'tail@{v}':spec for v,spec in self.puppet['tailViews'].items()}
            for key,spec in textures.items():
                source=(self.extension_directory/spec['src']).resolve()
                if not source.is_relative_to(self.extension_directory.resolve()):raise ValueError('无效的骨架贴图路径')
                im=QImage(str(source))
                if im.isNull() or max(im.width(),im.height())>4096:raise ValueError('无效的骨架贴图')
                self.puppet_images[key]=im
            for name,spec in self.puppet.get('headTurns',{}).items():
                source=(self.extension_directory/spec['src']).resolve()
                if not source.is_relative_to(self.extension_directory.resolve()):raise ValueError('无效的中间头图路径')
                image=QImage(str(source))
                if image.isNull() or max(image.width(),image.height())>4096:raise ValueError('无效的中间头图')
                part={'id':'head','box':spec['box'],'parent':'head','z':10}
                if 'warpY' in spec:part['warpY']=spec['warpY']
                data={'parts':[part],
                      'pivots':{'head':spec['neck']},'face':spec.get('face')}
                self.head_frames[name]=(data,{'head':image})
        extensions = self.extension_directory / "views.json"
        if extensions.exists():
            try:
                data = json.loads(extensions.read_text())
                for name, spec in data.get("views", {}).items():
                    if spec.get("rig"):
                        try:
                            self.rigs[name] = self._load_view_rig(spec["rig"])
                        except (OSError, ValueError, KeyError, TypeError):
                            self.view_errors.append(name)
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                self.view_errors.append("manifest")
            if self.view_errors:
                logging.warning("Optional model views unavailable: %d", len(self.view_errors))
        self.layered_head=None
        if (self.extension_directory/'head.json').exists():
            from .head import LayeredHead
            self.layered_head=LayeredHead(self)

    def _load_view_rig(self, filename):
        path = (self.extension_directory / filename).resolve()
        if not path.is_relative_to(self.extension_directory.resolve()):
            raise ValueError("无效的视角路径")
        data = json.loads(path.read_text())
        images = {}
        if data.get("schemaVersion") != 1 or not 1 <= len(data.get("parts", [])) <= 64:
            raise ValueError("不支持的视角绑定")
        def geometry(box):
            return isinstance(box,list) and len(box)==4 and all(type(v) in (int,float) and math.isfinite(v) and abs(v)<=2048 for v in box) and min(box[2:])>0
        face=data.get("face")
        if face is not None and (not isinstance(face,dict) or not geometry(face.get("box"))):
            raise ValueError("无效的面部锚点")
        if face:
            if not isinstance(face.get("features",{}),dict):
                raise ValueError("无效的五官锚点")
            for name,spec in face.get("features",{}).items():
                if not isinstance(spec,dict) or name not in self.parts or spec.get("source",name) not in self.images or not geometry(spec.get("box")):
                    raise ValueError("无效的五官坐标")
        for node, point in data.get("pivots", {}).items():
            if node not in self.pivots or len(point) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in point):
                raise ValueError("无效的视角枢轴")
        for part in data["parts"]:
            if not isinstance(part.get("id"),str) or part.get("id") in images or part.get("parent") not in self.pivots:
                raise ValueError("无效的视角层级")
            box = part.get("box", [])
            if len(box) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 2048 for v in box) or min(box[2:]) <= 0:
                raise ValueError("无效的视角坐标")
            if type(part.get("z")) not in (int,float) or not math.isfinite(part["z"]):
                raise ValueError("无效的图层顺序")
            if type(part.get('restRotation',0)) not in (int,float) or not math.isfinite(part.get('restRotation',0)):
                raise ValueError('无效的静态关节角')
            if part.get("warpY") and (len(part["warpY"])!=2 or any(type(v) not in (int,float) or not 0<v<1 for v in part["warpY"])):
                raise ValueError("无效的纵向变形")
            if part.get("cutout") and not geometry(part["cutout"]):
                raise ValueError("无效的遮罩")
            if part.get("sourcePart"):
                if part["sourcePart"] not in self.images:
                    raise ValueError("无效的原始部件")
                im=self.images[part["sourcePart"]]
            else:
                source = (path.parent / part["src"]).resolve()
                if not source.is_relative_to(self.extension_directory.resolve()):
                    raise ValueError("无效的视角图片路径")
                im = QImage(str(source))
            if im.isNull() or max(im.width(), im.height()) > 4096:
                raise ValueError("无效的视角图片")
            images[part["id"]] = self._region_image(im,part)
            arm=part.get('articulation')
            if arm is not None:
                if not isinstance(arm,dict) or set(arm.get('segments',{}))!={'upper','forearm','hand','point'}:
                    raise ValueError('无效的分段手臂')
                for name,segment in arm['segments'].items():
                    if not isinstance(segment,dict):raise ValueError('无效的手臂分片')
                    for key in ('rootUV','endUV'):
                        uv=segment.get(key)
                        if not isinstance(uv,list) or len(uv)!=2 or any(type(n) not in (int,float) or not math.isfinite(n) or not 0<=n<=1 for n in uv):
                            raise ValueError('无效的肘腕锚点')
                    scale=segment.get('scale')
                    if type(scale) not in (int,float) or not math.isfinite(scale) or not 0<scale<=2:
                        raise ValueError('无效的手臂比例')
                    source=(path.parent/segment['src']).resolve()
                    if not source.is_relative_to(self.extension_directory.resolve()):raise ValueError('无效的手臂分片路径')
                    texture=QImage(str(source))
                    if texture.isNull() or max(texture.width(),texture.height())>4096:raise ValueError('无效的手臂分片图片')
                    images[f'{part["id"]}#{name}']=texture
                target=arm.get('pointTarget');ray=arm['segments']['point'].get('indexRay')
                if any(not isinstance(v,list) or len(v)!=2 or any(type(n) not in (int,float) or not math.isfinite(n) for n in v) for v in (target,ray)):
                    raise ValueError('无效的分段指向目标')
            if not isinstance(part.get('variants',{}),dict):raise ValueError('无效的手势列表')
            for name,variant in part.get("variants",{}).items():
                if not isinstance(variant,dict) or name not in ("raised","point") or not geometry(variant.get("box")):
                    raise ValueError("无效的手势贴图")
                source=(path.parent/variant["src"]).resolve()
                if not source.is_relative_to(self.extension_directory.resolve()):
                    raise ValueError("无效的手势路径")
                image=QImage(str(source))
                if image.isNull() or max(image.width(),image.height())>4096:
                    raise ValueError("无效的手势图片")
                if any(type(variant.get(k,0)) not in (int,float) or not math.isfinite(variant.get(k,0)) for k in ("rotation","startRotation")):
                    raise ValueError("无效的手势角度")
                images[f'{part["id"]}@{name}']=image
                if variant.get('target'):
                    variant['rotation']=self._aim_angle(variant,data.get('pivots',{}).get(part['parent'],self.pivots[part['parent']]),image.size())
        return data, images

    @staticmethod
    def _region_image(image,part):
        """Keep source pixels in authored depth regions, without editing the PNG."""
        window=part.get('sourceWindow');fade=part.get('fadeBottom');fade_top=part.get('fadeTop')
        if window is None and fade is None and fade_top is None:return image
        if window is not None and (not isinstance(window,list) or len(window)!=4 or
            any(type(n) not in (int,float) or not math.isfinite(n) or not 0<=n<=1 for n in window) or
            min(window[2:])<=0 or window[0]+window[2]>1 or window[1]+window[3]>1):
            raise ValueError('无效的发束区域')
        if fade is not None and (not isinstance(fade,list) or len(fade)!=2 or
            any(type(n) not in (int,float) or not math.isfinite(n) for n in fade) or not 0<=fade[0]<fade[1]<=1):
            raise ValueError('无效的发束渐隐')
        if fade_top is not None and (not isinstance(fade_top,list) or len(fade_top)!=2 or
            any(type(n) not in (int,float) or not math.isfinite(n) for n in fade_top) or not 0<=fade_top[0]<fade_top[1]<=1):
            raise ValueError('无效的发根渐隐')
        result=QImage(image.size(),QImage.Format.Format_ARGB32_Premultiplied);result.fill(Qt.GlobalColor.transparent)
        p=QPainter(result)
        if window:
            x,y,w,h=window;p.setClipRect(QRectF(x*image.width(),y*image.height(),w*image.width(),h*image.height()))
        p.drawImage(0,0,image)
        if fade:
            gradient=QLinearGradient(0,0,0,image.height())
            gradient.setColorAt(0,QColor('white'));gradient.setColorAt(fade[0],QColor('white'))
            gradient.setColorAt(fade[1],QColor(255,255,255,0));gradient.setColorAt(1,QColor(255,255,255,0))
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            p.fillRect(result.rect(),gradient)
        if fade_top:
            gradient=QLinearGradient(0,0,0,image.height())
            gradient.setColorAt(0,QColor(255,255,255,0));gradient.setColorAt(fade_top[0],QColor(255,255,255,0))
            gradient.setColorAt(fade_top[1],QColor('white'));gradient.setColorAt(1,QColor('white'))
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            p.fillRect(result.rect(),gradient)
        p.end();return result

    @staticmethod
    def _aim_angle(spec,pivot,size):
        """Aim a painted index ray using its authored tip and direction."""
        values=[spec.get(k) for k in ('target','indexTipUV','indexRay')]
        if any(not isinstance(v,list) or len(v)!=2 or any(type(n) not in (int,float) or not math.isfinite(n) for n in v) for v in values):
            raise ValueError('无效的指向锚点')
        target,uv,ray=values;x,y,w,h=spec['box'];u=1-uv[0] if spec.get('flipX') else uv[0]
        vx,vy=x+u*w-pivot[0],y+uv[1]*h-pivot[1]
        dx,dy=ray[0]*w/size.width(),ray[1]*h/size.height()
        if spec.get('flipX'):dx=-dx
        length=math.hypot(dx,dy)
        if length<1e-6:raise ValueError('无效的食指方向')
        dx,dy=dx/length,dy/length
        tx,ty=target[0]-pivot[0],target[1]-pivot[1]
        dot=vx*dx+vy*dy;disc=dot*dot+tx*tx+ty*ty-vx*vx-vy*vy
        if disc<0:raise ValueError('指向目标超出该姿势的可用方向')
        distance=-dot+math.sqrt(disc)
        if distance<0:raise ValueError('指向目标位于手掌后方')
        return math.degrees(math.atan2(ty,tx)-math.atan2(vy+distance*dy,vx+distance*dx))

    def _joint(self, painter, node, pose, pivots=None):
        if node in PARENTS:
            self._joint(painter, PARENTS[node], pose, pivots)
        state = pose.transforms.get(node, {})
        x, y = (pivots or self.pivots).get(node, (425, 574))
        painter.translate(state.get("x", 0), state.get("y", 0))
        painter.translate(x, y)
        painter.rotate(state.get("a", 0))
        painter.scale(state.get("sx", 1), state.get("sy", 1))
        painter.translate(-x, -y)

    @staticmethod
    def _line(painter, points, width=3, color=INK):
        pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath(QPointF(*points[0]))
        if len(points) == 3:
            path.quadTo(QPointF(*points[1]), QPointF(*points[2]))
        else:
            for point in points[1:]:
                path.lineTo(QPointF(*point))
        painter.drawPath(path)

    @staticmethod
    def _heart(painter, x, y, radius):
        painter.save()
        painter.translate(x, y)
        painter.scale(radius, radius)
        path = QPainterPath(QPointF(0, .9))
        path.cubicTo(-1.8, -.4, -.9, -1.6, 0, -.5)
        path.cubicTo(.9, -1.6, 1.8, -.4, 0, .9)
        painter.setPen(QPen(QColor("#a786cf"), .12))
        painter.setBrush(QColor("#f5e8ff"))
        painter.drawPath(path)
        painter.restore()

    def _feature(self, painter, name):
        painter.drawImage(QRectF(*self.parts[name]["box"]), self.images[name])

    def _face(self, pose, lashes=False, one_eye=False, layout=None):
        if pose.face_weights:
            result=None;total=0.
            for name,weight in pose.face_weights.items():
                if weight<1e-6:continue
                frame=self._face(replace(pose,expression=name,face_weights={}),lashes,one_eye,layout)
                result=frame if result is None else self._mix(result,frame,weight/(total+weight))
                total+=weight
            if result is not None:return result
        if pose.expression_from and pose.expression_mix<1:
            first=self._face(replace(pose,expression=pose.expression_from,expression_from=''),lashes,one_eye,layout)
            second=self._face(replace(pose,expression_from=''),lashes,one_eye,layout)
            return self._mix(first,second,pose.expression_mix)
        image = QImage(230, 150, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(-270, -315)
        layout = layout or {}
        features = dict(self.parts)
        for name, spec in layout.get("features", {}).items():
            x, y, w, h = spec["box"]
            features[name] = {**spec, "box": [270+x,315+y,w,h]}
        def feature(name):
            spec = features[name]
            im = self.images[spec.get("source", name)]
            if spec.get("flipX"):
                im = im.flipped(Qt.Orientation.Horizontal)
            return im
        def draw_feature(name):
            painter.drawImage(QRectF(*features[name]["box"]), feature(name))
        face = pose.expression
        for index, side in enumerate(("far", "near")):
            if one_eye and index == 0:
                continue
            part = features[f"eye-{side}-white"]
            x, y, w, h = part["box"]
            alpha=layout.get('eyeOpacity',[1.,1.])[index]
            if w<1 or h<1 or alpha<.001:continue
            painter.save();painter.setOpacity(painter.opacity()*alpha)
            cx, cy = x+w/2, y+h/2
            closed = pose.eye_closed or face in ("happy", "cry", "flustered") or (face == "wink" and index == layout.get('winkEye',1 if one_eye else 0))
            openness = max(.02, 1-pose.blink)
            if face in ("sleepy", "smug"):
                openness *= .5
            if face in ("angry", "determined"):
                openness *= .62 if face == "angry" else .84
            if face == "sad":
                openness *= .8
            if face == "surprised":
                openness *= 1.08
            if face == "dizzy" and not lashes:
                points = []
                for n in range(80):
                    phase = n/79*math.pi*5 + pose.time
                    r = n/79*w*.43
                    points.append((cx+math.cos(phase)*r, cy+math.sin(phase)*r))
                self._line(painter, points, 3.5)
            elif closed or pose.blink>.985:
                if lashes:
                    if face == "flustered":
                        sign = 1 if index == 0 else -1
                        self._line(painter, [(cx-sign*w*.38, cy-12), (cx+sign*w*.32, cy), (cx-sign*w*.38, cy+12)], 5)
                    else:
                        # Preserve the original painted thick lash when closing the eye.
                        painter.save()
                        painter.translate(cx, cy+3)
                        painter.scale(1, .65)
                        painter.translate(-cx, -cy-3)
                        draw_feature(f"eye-{side}-lash")
                        painter.restore()
            else:
                painter.save()
                painter.translate(cx, cy+3)
                if face in ('angry','determined','worried'):
                    painter.rotate((10 if face=='angry' else 6 if face=='determined' else -7)*(1 if index==0 else -1))
                painter.scale(1, openness)
                painter.translate(-cx, -cy-3)
                if lashes:
                    draw_feature(f"eye-{side}-lash")
                else:
                    eye = QImage(int(w), int(h), QImage.Format.Format_ARGB32_Premultiplied)
                    eye.fill(Qt.GlobalColor.transparent)
                    ep = QPainter(eye)
                    ep.drawImage(QRectF(0, 0, w, h), feature(f"eye-{side}-white"))
                    ep.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
                    ix, iy, iw, ih = features[f"eye-{side}-iris"]["box"]
                    gaze_x, gaze_y = pose.gaze
                    if face in ("shy", "pout"):
                        gaze_x = -.7
                    if face == "thinking":
                        gaze_y = -.8
                    iris_scale=.58 if face=='scared' else .88 if face=='determined' else 1.
                    ep.drawImage(QRectF(ix-x+gaze_x*5+iw*(1-iris_scale)/2, iy-y+gaze_y*4+ih*(1-iris_scale)/2, iw*iris_scale, ih*iris_scale), feature(f"eye-{side}-iris"))
                    if face == "love":
                        self._heart(ep, w*.55, h*.47, w*.24)
                    if face == "excited":
                        points = []
                        for n in range(8):
                            angle = n*math.pi/4
                            r = 12 if n % 2 == 0 else 3
                            points.append(QPointF(w*.55+math.cos(angle)*r, h*.42+math.sin(angle)*r))
                        ep.setPen(Qt.PenStyle.NoPen)
                        ep.setBrush(Qt.GlobalColor.white)
                        ep.drawPolygon(QPolygonF(points))
                    ep.end()
                    painter.drawImage(QPointF(x, y), eye)
                painter.restore()
            if lashes:
                bx, by, bw, bh = features[f"brow-{side}"]["box"]
                painter.save()
                painter.translate(bx+bw/2, by+bh/2 + (-7 if face == "surprised" else -5 if face == "confused" and index else 0))
                if face in ("angry", "determined"):
                    painter.rotate((18 if face == "angry" else 8)*(1 if index == 0 else -1))
                elif face in ("sad", "worried", "scared", "cry"):
                    painter.rotate(-13 if index == 0 else 13)
                painter.translate(-bx-bw/2, -by-bh/2)
                draw_feature(f"brow-{side}")
                painter.restore()
            painter.restore()
        if not lashes:
            if face in ("shy", "love", "flustered"):
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(235, 143, 169, 85))
                blush = layout.get("blush", [[37,101,26,9],[164,101,26,9]])
                for index, (x,y,w,h) in enumerate(blush):
                    if not one_eye or index == 1:
                        painter.save();painter.setOpacity(painter.opacity()*layout.get('eyeOpacity',[1.,1.])[index])
                        painter.drawEllipse(QRectF(270+x,315+y,w,h));painter.restore()
            mx,my,mw,mh = features["mouth"]["box"]
            mouth_x,mouth_y = mx+mw/2,my+mh/2
            if face=='pout' and pose.speech<.08:
                painter.setPen(QPen(INK,1.8));painter.setBrush(QColor('#e6a5b7'))
                path=QPainterPath(QPointF(mouth_x-4,mouth_y));path.quadTo(QPointF(mouth_x+6,mouth_y-5),QPointF(mouth_x+3,mouth_y))
                path.quadTo(QPointF(mouth_x+7,mouth_y+5),QPointF(mouth_x-4,mouth_y+2));painter.drawPath(path)
            elif pose.speech > .05 or face in ("surprised", "scared", "sleepy", "cry"):
                painter.setPen(QPen(INK, 1.5))
                painter.setBrush(QColor("#aa6f85"))
                height = 3 + pose.speech*8 + (5 if face in ("surprised", "cry") else 0)
                width=7+pose.speech*(8 if face in ('happy','smug','excited','love') else 3)
                if face in ('happy','smug','excited','love'):
                    path=QPainterPath(QPointF(mouth_x-width/2,mouth_y-height/3))
                    path.quadTo(QPointF(mouth_x,mouth_y+height),QPointF(mouth_x+width/2,mouth_y-height/3));path.closeSubpath();painter.drawPath(path)
                else:painter.drawEllipse(QRectF(mouth_x-width/2, mouth_y-height/2, width, height))
            elif face in ("happy", "wink", "love", "excited", "smug"):
                self._line(painter, [(mouth_x-5,mouth_y-1),(mouth_x,mouth_y+8),(mouth_x+7,mouth_y-2)],1.8)
            elif face in ("sad", "angry", "worried", "determined"):
                if face == "determined":
                    self._line(painter,[(mouth_x-4,mouth_y+1),(mouth_x+4,mouth_y+1)],1.8)
                else:
                    self._line(painter,[(mouth_x-5,mouth_y+4),(mouth_x,mouth_y-2),(mouth_x+5,mouth_y+4)],1.8)
            else:
                draw_feature("mouth")
            if face in ("sad", "cry"):
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(125, 192, 230, 175))
                for index,(x,y) in enumerate(layout.get("tears",[[57,93],[164,93]])):
                    if one_eye and index == 0:
                        continue
                    painter.save();painter.setOpacity(painter.opacity()*layout.get('eyeOpacity',[1.,1.])[index])
                    yy=315+y+(0 if face == "cry" else 3+(pose.time*25 % 25))
                    painter.drawRoundedRect(QRectF(270+x, yy, 7, 30 if face == "cry" else 10), 3, 3)
                    painter.restore()
        painter.end()
        return image

    def _skin_mask(self, view, data, images):
        """Keep facial overlays on the painted skin, behind baked hair strands."""
        if view in self.face_masks:
            return self.face_masks[view]
        part=next(p for p in data["parts"] if p["id"]=="head")
        # Only the face region needs classifying. Sampling at twice the overlay
        # resolution avoids scanning megapixel hair and horn textures mid-turn.
        sample=QImage(460,300,QImage.Format.Format_RGBA8888);sample.fill(Qt.GlobalColor.transparent)
        mp=QPainter(sample);mp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        x,y,w,h=data["face"]["box"]
        mp.scale(460/w,300/h);mp.translate(-x,-y)
        if part.get('warpY'):
            x,y,w,h=part['box'];a,b=part['warpY']
            texture=images['head']
            mp.drawImage(QRectF(x,y,w,h*b),texture,QRectF(0,0,texture.width(),texture.height()*a))
            mp.drawImage(QRectF(x,y+h*b,w,h*(1-b)),texture,QRectF(0,texture.height()*a,texture.width(),texture.height()*(1-a)))
        else:mp.drawImage(QRectF(*part['box']),images['head'])
        mp.end()
        rgba=bytes(sample.constBits());pixels=bytearray(len(rgba))
        for i in range(0,len(rgba),4):
            r,g,b,a=rgba[i:i+4]
            if a and r>=225 and g>=195 and r>=g+2 and r>=b+3:pixels[i:i+4]=bytes((255,255,255,a))
        mask=QImage(pixels,460,300,460*4,QImage.Format.Format_RGBA8888).copy().scaled(230,150,
                Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation)
        if data['face'].get('flip'):mask=mask.flipped(Qt.Orientation.Horizontal)
        self.face_masks[view]=mask
        return mask

    def _mesh(self, painter, image, box, amplitude, start=0):
        x, y, w, h = box
        # Warp the continuous texture before its final affine transform. Painting
        # clipped strips directly at fractional window scale leaves hairline seams.
        # Rows share an immutable source and retain alpha; no GPU readback occurs.
        amplitude = round(amplitude*2)/2
        key = (image.cacheKey(), int(w), int(h), amplitude, start)
        warped = self.warp_cache.get(key)
        padding = 32
        if warped is None:
            source = image.scaled(int(w), int(h), Qt.AspectRatioMode.IgnoreAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
            warped = QImage(int(w)+padding*2, int(h), QImage.Format.Format_ARGB32_Premultiplied)
            warped.fill(Qt.GlobalColor.transparent)
            warp_painter = QPainter(warped)
            warp_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            for row in range(source.height()):
                v = max(0,(row/max(1,source.height()-1)-start)/(1-start))
                displacement = amplitude*v*math.sin(v*math.pi/2)
                warp_painter.drawImage(QRectF(padding+displacement, row, w, 1), source,
                                       QRectF(0, row, w, 1))
            warp_painter.end()
            if len(self.warp_cache) >= 24:
                del self.warp_cache[next(iter(self.warp_cache))]
            self.warp_cache[key] = warped
        painter.drawImage(QRectF(x-padding, y, w+padding*2, h), warped)

    def _draw_texture(self,painter,box,image):
        # QPainter's bilinear sampling alone aliases 1K artwork down to a 20px
        # sleeve. Area-filtered mip levels retain opaque fills and clean lines.
        transform=painter.worldTransform();w,h=box[2:]
        dw=abs(w)*math.hypot(transform.m11(),transform.m12())
        dh=abs(h)*math.hypot(transform.m21(),transform.m22())
        divisor=1
        while image.width()/(divisor*2)>=max(1,dw*1.5) and image.height()/(divisor*2)>=max(1,dh*1.5):divisor*=2
        if divisor>1:
            key=(image.cacheKey(),divisor);texture=self.texture_cache.get(key)
            if texture is None:
                texture=image.scaled(max(1,image.width()//divisor),max(1,image.height()//divisor),
                    Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation)
                if len(self.texture_cache)>=64:del self.texture_cache[next(iter(self.texture_cache))]
                self.texture_cache[key]=texture
            image=texture
        painter.drawImage(QRectF(*box),image)

    @staticmethod
    def _mix(first,second,amount):
        result=QImage(first.size(),QImage.Format.Format_ARGB32_Premultiplied)
        result.fill(Qt.GlobalColor.transparent)
        blend=QPainter(result);blend.setOpacity(1-amount);blend.drawImage(0,0,first);blend.end()
        # Weight before PLUS: Qt applies opacity after composition and would
        # otherwise saturate then interpolate, leaving the body translucent.
        weighted=QImage(second.size(),QImage.Format.Format_ARGB32_Premultiplied)
        weighted.fill(Qt.GlobalColor.transparent)
        weight=QPainter(weighted);weight.setOpacity(amount);weight.drawImage(0,0,second);weight.end()
        blend=QPainter(result);blend.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        blend.drawImage(0,0,weighted);blend.end()
        return result

    def render(self, pose, width=384, height=None, debug=False):
        height = width if height is None else height
        # Authored direction frames preserve the character's silhouettes. Small
        # pitch/yaw and all skeletal actions still deform within each frame.
        # Continuous camera inbetweens require accepted, matching artwork.
        if pose.blend_view and pose.view_mix>0:
            view=pose.view if pose.view_mix<.5 else pose.blend_view
            return self.render(replace(pose,view=view,blend_view='',view_mix=0,camera_angle=None),width,height,debug)
        if pose.camera_angle is not None:
            view=min(VIEW_ANGLES,key=lambda name:abs((VIEW_ANGLES[name]-pose.camera_angle+180)%360-180))
            return self.render(replace(pose,view=view,camera_angle=None),width,height,debug)
        image = QImage(max(1, int(width)), max(1, int(height)), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        painter.scale(width/DESIGN_SIZE, height/DESIGN_SIZE)
        painter.translate(150+pose.root_x, 220+pose.root_y)
        painter.translate(*pose.root_anchor)
        painter.rotate(pose.root_angle)
        painter.translate(-pose.root_anchor[0], -pose.root_anchor[1])
        if pose.view in self.rigs:
            self._render_view(painter, pose)
        else:
            self._render_source(painter, pose)
        if debug:
            painter.setPen(QPen(QColor("#ef476f"), 3))
            debug_pivots={**self.pivots,**(self.rigs.get(pose.view,({},{}))[0].get("pivots",{}))}
            for name, point in debug_pivots.items():
                painter.save()
                self._joint(painter, name, pose, debug_pivots)
                painter.drawEllipse(QPointF(*point), 7, 7)
                painter.restore()
        painter.end()
        return image

    def _sole(self,view,node):
        data=self.rigs.get(view,({},{}))[0];parts=data.get('parts',self.parts.values())
        for part in parts:
            if part['parent']!=node:continue
            spec=self.puppet['legs'][view].get(part['id'])
            if spec:
                x,y,w,h=part['box'];u,v=spec['soleUV']
                return x+(1-u if part.get('flipX') else u)*w,y+v*h
        return None

    @staticmethod
    def _neighbors(angle,choices=VIEW_ANGLES):
        ordered=sorted((value,name) for name,value in choices.items());position=angle%360
        before=[pair for pair in ordered if pair[0]<=position]
        low=before[-1] if before else (ordered[-1][0]-360,ordered[-1][1])
        after=[pair for pair in ordered if pair[0]>position]
        high=after[0] if after else (ordered[0][0]+360,ordered[0][1])
        return low[1],high[1],(position-low[0])/(high[0]-low[0])




    @staticmethod
    def _in_scope(part,scope):
        head=part['parent'] in ('head','hairBack','hairFront','ahoge')
        if scope=='rear-base':return part['parent'] not in ('head','hairFront','ahoge')
        if scope=='back-hair':return part['parent']=='hairBack'
        if scope=='front-head':return head and part['parent']!='hairBack'
        return scope=='all' or head==(scope=='head')

    def _render_leg(self,painter,part,image,pose,pivots):
        spec=self.puppet.get('legs',{}).get(pose.view,{}).get(part['id'])
        if not spec:return False
        x,y,w,h=part['box']
        def vertex(uv):
            u,v=uv
            return (x+(1-u if part.get('flipX') else u)*w,y+v*h)
        rest=[vertex(spec[k]) for k in ('hipUV','kneeUV','ankleUV','soleUV')]
        state=pose.legs.get(part['parent'],{})
        if max(abs(v) for v in (*pose.pelvis,*state.values()))<.001:
            if part.get('flipX'):
                painter.save();painter.translate(x+w,y);painter.scale(-1,1)
                self._draw_texture(painter,[0,0,w,h],image);painter.restore()
            else:self._draw_texture(painter,part['box'],image)
            return True
        hip=(rest[0][0]+pose.pelvis[0],rest[0][1]+pose.pelvis[1])
        sole=(rest[3][0]+state.get('x',0),rest[3][1]+state.get('y',0))
        foot=rotate((rest[3][0]-rest[2][0],rest[3][1]-rest[2][1]),math.radians(state.get('foot',0)))
        ankle=(sole[0]-foot[0],sole[1]-foot[1])
        knee,actual=solve_leg(hip,ankle,math.dist(rest[0],rest[1]),math.dist(rest[1],rest[2]),view_angle=VIEW_ANGLES[pose.view])
        if not pose.contacts[0 if part['parent']=='legFar' else 1]:
            sole=(sole[0]+actual[0]-ankle[0],sole[1]+actual[1]-ankle[1])
            # Intersect the same reach circle with the actual world floor.
            # The line normal includes the root rotation about its own anchor.
            angle=math.radians(pose.root_angle);normal=(math.sin(angle),math.cos(angle));tangent=(normal[1],-normal[0])
            dot=lambda a,b:a[0]*b[0]+a[1]*b[1]
            floor=rest[3][1]-pose.root_y-pose.root_anchor[1]+dot(normal,pose.root_anchor)
            if dot(normal,sole)>floor:
                radius=math.dist(hip,actual[:2]);dy=max(-radius,min(radius,floor-dot(normal,foot)-dot(normal,hip)))
                sign=1 if dot(tangent,(actual[0]-hip[0],actual[1]-hip[1]))>=0 else -1
                dx=sign*math.sqrt(max(0.,radius*radius-dy*dy))
                ankle=tuple(hip[i]+tangent[i]*dx+normal[i]*dy for i in (0,1))
                knee,actual=solve_leg(hip,ankle,math.dist(rest[0],rest[1]),math.dist(rest[1],rest[2]),view_angle=VIEW_ANGLES[pose.view])
                sole=(actual[0]+foot[0],actual[1]+foot[1])
        posed=[hip,knee,actual,sole]
        kv,av=spec['kneeUV'][1],spec['ankleUV'][1]
        def mapping(point):
            px,py=point;v=(py-y)/h
            if part.get('flipX'):px=x+w-(px-x)
            lower=smooth((v-kv+.055)/.11);boot=smooth((v-av+.035)/.07)
            return skin_point((px,py),rest,posed,(1-lower,lower*(1-boot),boot))
        draw_mesh(painter,image,part['box'],mapping,columns=3,rows=18)
        return True

    def _render_tail(self,painter,pose,foreground=False):
        painter.setOpacity(painter.opacity()*(1-smooth((pose.turn_tail-.98)/.02)))
        if foreground and pose.turn_tail>=.25:return
        spec=self.puppet['tailViews'][pose.view]
        rest,posed=self._tail_geometry(pose)
        skin=self.tail_skins.get(pose.view)
        if skin is None:
            skin=TailSkin(self.puppet_images[f'tail@{pose.view}'],[spec[k] for k in ('rootUV','midUV','lowUV','thinUV','leafBaseUV','tipUV')],resolution=256 if pose.view=='back' else 128)
            self.tail_skins[pose.view]=skin
        mapper=self._tail_mapping(pose,rest,posed,skin,spec['box'])
        image=self.puppet_images[f'tail@{pose.view}']
        if foreground:image=self._tail_foreground(pose.view,image)
        if foreground:painter.setOpacity(painter.opacity()*(1-smooth(pose.turn_tail/.25)))
        draw_mesh(painter,image,spec['box'],mapper,columns=16 if pose.view=='back' else 8,rows=24 if pose.view=='back' else 12)

    def _tail_foreground(self,view,image):
        key=f'tail-foreground@{view}'
        if key in self.puppet_images:return self.puppet_images[key]
        spec=self.puppet['tailViews'][view]['occlusion']['sourceHalfPlane']
        point=spec['point'];normal=spec['normal']
        polygon=[(0.,0.),(float(image.width()),0.),(float(image.width()),float(image.height())),(0.,float(image.height()))]
        clipped=[]
        for a,b in zip(polygon,polygon[1:]+polygon[:1]):
            da=(a[0]-point[0])*normal[0]+(a[1]-point[1])*normal[1]
            db=(b[0]-point[0])*normal[0]+(b[1]-point[1])*normal[1]
            if da>=0:clipped.append(a)
            if (da>=0)!=(db>=0):
                t=da/(da-db);clipped.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
        result=QImage(image.size(),QImage.Format.Format_ARGB32_Premultiplied);result.fill(Qt.GlobalColor.transparent)
        p=QPainter(result);path=QPainterPath();path.addPolygon(QPolygonF([QPointF(*xy) for xy in clipped]));path.closeSubpath()
        p.setClipPath(path);p.drawImage(0,0,image);p.end()
        self.puppet_images[key]=result;return result

    def _tail_geometry(self,pose):
        spec=self.puppet['tailViews'][pose.view];x,y,w,h=spec['box']
        rest=[(x+spec[k][0]*w,y+spec[k][1]*h) for k in ('rootUV','midUV','lowUV','thinUV','leafBaseUV','tipUV')]
        pivots={**self.pivots,**self.rigs.get(pose.view,({},{}))[0].get('pivots',{})}
        matrix=QTransform();self._joint(matrix,'upper',pose,pivots)
        angle=VIEW_ANGLES[pose.view] if pose.camera_angle is None else pose.camera_angle
        attachment=coccyx_point(angle,pose.seat)
        root=matrix.map(QPointF(*attachment));delta=(root.x()-rest[0][0],root.y()-rest[0][1])
        lengths=[0.]
        for a,b in zip(rest,rest[1:]):lengths.append(lengths[-1]+math.dist(a,b))
        posed=[(root.x(),root.y())]
        crouch=smooth(max(0.,delta[1])/180.)
        outward=1 if rest[-2][0]>=rest[0][0] else -1
        for i,(a,b) in enumerate(zip(rest[:-2],rest[1:-1])):
            t=lengths[i+1]/lengths[-2];angle=math.atan2(b[1]-a[1],b[0]-a[0])
            if i<2:
                target=(0. if i==0 else .3) if outward>0 else (math.pi if i==0 else math.pi-.3)
                angle+=((target-angle+math.pi)%(2*math.pi)-math.pi)*crouch
            angle+=math.sin(pose.time*2.4-t*3.7)*(.7+pose.tail_energy)*t*t*.025
            length=math.dist(a,b)
            posed.append((posed[-1][0]+math.cos(angle)*length,posed[-1][1]+math.sin(angle)*length))
        leaf=rotate((rest[-1][0]-rest[-2][0],rest[-1][1]-rest[-2][1]),
                    math.radians(math.sin(pose.time*2.4-3.7)*(.7+pose.tail_energy)*2))
        posed.append((posed[-1][0]+leaf[0],posed[-1][1]+leaf[1]))
        if pose.turn_tail:
            hidden=[(root.x()+i*2,root.y()+i*8) for i in range(len(posed))]
            posed=[tuple(a+(b-a)*pose.turn_tail for a,b in zip(point,target)) for point,target in zip(posed,hidden)]
        posed=self._ground_tail(pose,rest,posed)
        return rest,posed

    def _tail_skin(self,view):
        skin=self.tail_skins.get(view)
        if skin is None:
            spec=self.puppet['tailViews'][view]
            skin=TailSkin(self.puppet_images[f'tail@{view}'],[spec[k] for k in ('rootUV','midUV','lowUV','thinUV','leafBaseUV','tipUV')],resolution=256 if view=='back' else 128)
            self.tail_skins[view]=skin
        return skin

    def _ground_tail(self,pose,rest,posed):
        skin=self._tail_skin(pose.view);x,y,w,h=self.puppet['tailViews'][pose.view]['box']
        root=posed[0];anchor=pose.root_anchor;angle=math.radians(pose.root_angle)
        points=[]
        for u,v,weights in skin.boundary:
            px,py=skin_point((x+u*w,y+v*h),rest,posed,weights)
            points.append((px-root[0],py-root[1]))
        _,root_world_y=rotate((root[0]-anchor[0],root[1]-anchor[1]),angle)
        root_world_y+=anchor[1]+pose.root_y
        def bottom(offset):
            c,s=math.cos(angle+offset),math.sin(angle+offset)
            return root_world_y+max(px*s+py*c for px,py in points)
        if bottom(0)<=967:return posed
        options=[]
        for sign in (-1,1):
            for degrees in range(2,81,2):
                value=math.radians(degrees)*sign
                if bottom(value)<=967:
                    low,high=0.,abs(value)
                    for _ in range(12):
                        mid=(low+high)/2
                        if bottom(mid*sign)>967:low=mid
                        else:high=mid
                    options.append(high*sign);break
        if not options:return posed
        offset=min(options,key=abs)
        result=[]
        for point in posed:
            xx,yy=rotate((point[0]-root[0],point[1]-root[1]),offset)
            result.append((root[0]+xx,root[1]+yy))
        return result

    def _tail_mapping(self,pose,rest,posed,skin=None,box=None):
        spec=self.puppet['tailViews'][pose.view]
        if skin is None:
            skin=self._tail_skin(pose.view)
        box=box or spec['box']
        angle=math.radians(pose.root_angle);anchor=pose.root_anchor
        def mapping(point):
            bx,by,bw,bh=box;weights=skin.weights((point[0]-bx)/bw,(point[1]-by)/bh)
            x,y=skin_point(point,rest,posed,weights)
            wx,wy=rotate((x-anchor[0],y-anchor[1]),angle)
            wy+=anchor[1]+pose.root_y
            if wy>965:
                ground=965+4*(1-math.exp(-(wy-965)/4))
                x,y=rotate((wx,ground-anchor[1]-pose.root_y),-angle)
                x+=anchor[0];y+=anchor[1]
            return x,y
        return mapping

    def _render_garment(self,painter,part,image,pose,pivots):
        matrix=QTransform();self._joint(matrix,'upper',pose,pivots)
        waist=683.;hem=969.
        def mapping(point):
            x,y=point;moved=matrix.map(QPointF(x,y))
            hem_weight=smooth((y-waist)/max(1,hem-waist))
            xx=moved.x()*(1-hem_weight)+x*hem_weight
            yy=moved.y()*(1-hem_weight)+y*hem_weight
            if pose.seat>0 and y>574:
                attachment=matrix.map(QPointF(425,574))
                folded=attachment.y()+(y-574)*(969-attachment.y())/(969-574)
                weight=smooth(pose.seat/.35);yy=yy*(1-weight)+folded*weight
            # Cloth follows the moving waist but folds above a grounded hem.
            spread=(x-425)*.45*pose.seat*math.sin(hem_weight*math.pi/2)
            sway=pose.cloth*math.sin(hem_weight*math.pi)
            if pose.motion in ('walk','run','dance'):
                forward=-math.sin(math.radians(VIEW_ANGLES[pose.view]))
                swing=max(-state.get('y',0) for state in pose.legs.values())
                front=425+forward*100
                yy-=swing*.55*hem_weight*math.exp(-((x-front)/145)**2)
            return xx+spread+sway,yy
        active=pose.motion in ('walk','run','dance')
        draw_mesh(painter,image,part['box'],mapping,columns=5 if active else 2,rows=16)

    def _render_projected_head(self,painter,pose,data=None,rig_override=None):
        pivots={**self.pivots,**(data or {}).get('pivots',{})}
        if self.layered_head:
            self._render_head_at_angle(painter,pose,pose.camera_angle if pose.camera_angle is not None else VIEW_ANGLES[pose.view],pivots['head']);return
        if pose.camera_angle is not None:
            self._render_head_at_angle(painter,pose,pose.camera_angle,pivots['head']);return
        parts=(data or {}).get('parts',list(self.parts.values()))
        head=[p for p in parts if p['parent'] in ('head','hairFront','ahoge')]
        head=head+[{'box':((data or {}).get('face') or {}).get('box',[270,315,230,150])}]
        x=min(p['box'][0] for p in head)-24;y=min(p['box'][1] for p in head)-24
        w=max(p['box'][0]+p['box'][2] for p in head)-x+24;h=max(p['box'][1]+p['box'][3] for p in head)-y+24
        image=QImage(math.ceil(w),math.ceil(h),QImage.Format.Format_ARGB32_Premultiplied);image.fill(Qt.GlobalColor.transparent)
        hp=QPainter(image);hp.setRenderHints(painter.renderHints());hp.translate(-x,-y)
        local=replace(pose,head_pitch=0.,head_yaw=0.,look_back=0.,
            transforms={**pose.transforms,'upper':{},'head':{}})
        if data:self._render_view(hp,local,scope='front-head',rig_override=rig_override)
        else:self._render_source(hp,local,scope='front-head')
        hp.end()
        core=next((p['box'] for p in head if p.get('id')=='head'),[213,65,400,475])
        projection_view=self.puppet.get('headTurns',{}).get(pose.view,{}).get('baseView',pose.view)
        def mapper(point):
            x,y=head_point(point,pivots['head'],core,pose.head_pitch,pose.head_yaw,projection_view)
            frame=self.puppet.get('headTurns',{}).get(pose.view,{})
            direction=1 if frame.get('baseView')=='left' else -1
            if frame and (x-pivots['head'][0])*direction>0:
                x=pivots['head'][0]+(x-pivots['head'][0])*frame.get('backScale',1.)
            return x,y
        painter.save();self._joint(painter,'head',pose,pivots)
        if abs(pose.head_pitch)+abs(pose.head_yaw)<.001 and pose.view not in self.head_frames:self._draw_texture(painter,[x,y,w,h],image)
        else:draw_mesh(painter,image,[x,y,w,h],mapper,columns=12,rows=16)
        painter.restore()

    def _render_source(self, painter, pose, scope='all'):
        layers = [(part["z"], name, part) for name, part in self.parts.items()
                  if part["parent"] != "features" and name != "nose"]
        layers += [(20.5, "@eyes", {"parent": "head", "box": [270, 315, 230, 150]}),
                   (27.5, "@lashes", {"parent": "head", "box": [270, 315, 230, 150]})]
        layers=[layer for layer in layers if self._in_scope(layer[2],scope)]
        projected=scope=='all'
        if projected:
            layers=[layer for layer in layers if self._in_scope(layer[2],'rear-base')]
            layers.append((27.5,'@projected-head',{'parent':'head','box':[0,0,1,1]}))
        if self.puppet and scope in ('all','body','rear-base'):
            layers=[layer for layer in layers if layer[1]!='sit']
        for _, name, part in sorted(layers, key=lambda p: p[0]):
            painter.save()
            if name=='@projected-head':
                self._render_projected_head(painter,pose);painter.restore();continue
            if self.puppet and name=='tail':
                self._render_tail(painter,pose);painter.restore();continue
            if self.puppet and name in ('leg-far','leg-near'):
                self._render_leg(painter,part,self.images[name],pose,self.pivots);painter.restore();continue
            if self.puppet and name in ('skirt-far','skirt-near','apron'):
                self._render_garment(painter,part,self.images[name],pose,self.pivots);painter.restore();continue
            seated=smooth(pose.seat)
            if name == "sit":
                painter.setOpacity(seated)
            elif not self.puppet and name in ("tail","leg-far","leg-near","skirt-far","skirt-near","apron","wing-far","wing-near"):
                painter.setOpacity(1-seated)
            self._joint(painter, part["parent"], pose)
            if name.startswith("@"):
                painter.drawImage(QRectF(*part["box"]), self._face(pose, name == "@lashes"))
            elif part["parent"] in ("hairBack", "hairFront"):
                self._mesh(painter, self.images[name], part["box"], pose.transforms[part["parent"]]["warp"])
            else:
                painter.drawImage(QRectF(*part["box"]), self.images[name])
            painter.restore()
        # Status accents are independent of the expression atlas.
        if scope in ('body','back-hair','all'):return
        painter.save()
        self._joint(painter, "head", pose)
        painter.setPen(QPen(QColor("#8c76b7"), 3))
        font = painter.font()
        font.setPixelSize(48)
        painter.setFont(font)
        opacity=painter.opacity()
        for expression,weight in (pose.face_weights or {pose.expression:1.}).items():
            accent={"confused":"?","surprised":"!","thinking":"···","worried":"◦","angry":"♯"}.get(expression,'')
            if pose.eye_closed:accent='z'
            painter.setOpacity(opacity*weight)
            painter.drawText(QPointF(565,220+math.sin(pose.time*2)*3),accent)
        painter.restore()

    def _head_accent(self,painter,pose,pivots):
        painter.save();self._joint(painter,'head',pose,pivots)
        f=painter.font();f.setPixelSize(40);painter.setFont(f);painter.setPen(QColor('#8c76b7'))
        opacity=painter.opacity()
        for expression,weight in (pose.face_weights or {pose.expression:1.}).items():
            accent={'confused':'?','thinking':'···','worried':'◦','angry':'♯','surprised':'!'}.get(expression,'')
            painter.setOpacity(opacity*weight);painter.drawText(QPointF(pivots['head'][0]+140,220),accent)
        painter.restore()

    def _render_look_back(self,painter,pose,data):
        """Keep the rear-quarter body while the head turns over its shoulder."""
        current={**self.pivots,**data.get('pivots',{})}
        choices=(pose.view,'left','front-left') if pose.view=='back-left' else (pose.view,'right','front-right')
        self._render_view(painter,replace(pose,look_back=0),scope='rear-base')
        start=pose.camera_angle if pose.camera_angle is not None else VIEW_ANGLES[pose.view];direction=-1 if pose.view=='back-left' else 1
        self._render_head_at_angle(painter,replace(pose,look_back=0),start+direction*90*pose.look_back,current['head'])

    def _render_head_at_angle(self,painter,pose,angle,target_neck):
        if self.layered_head:
            if pose.camera_angle is not None:
                a,b,t=self._neighbors(pose.camera_angle)
                an=self.rigs.get(a,({},{}))[0].get('pivots',{}).get('head',self.pivots['head'])
                bn=self.rigs.get(b,({},{}))[0].get('pivots',{}).get('head',self.pivots['head'])
                target_neck=tuple(x+(y-x)*t for x,y in zip(an,bn))
            self.layered_head.draw(painter,pose,angle,target_neck)
            self._head_accent(painter,pose,{**self.pivots,'head':target_neck});return
        choices={**{name:VIEW_ANGLES[name] for name in VIEW_ANGLES},
                 **{name:spec['angle'] for name,spec in self.puppet.get('headTurns',{}).items()}}
        view=min(choices,key=lambda name:abs((angle-choices[name]+180)%360-180))
        offset=(angle-choices[view]+180)%360-180
        data,images=self._head_material(view)
        override=(data,images)
        ordered=sorted((value,name) for name,value in choices.items())
        position=angle%360;before=[pair for pair in ordered if pair[0]<=position]
        low=before[-1] if before else (ordered[-1][0]-360,ordered[-1][1])
        after=[pair for pair in ordered if pair[0]>position]
        high=after[0] if after else (ordered[0][0]+360,ordered[0][1])
        amount=(position-low[0])/(high[0]-low[0])
        first_data=self._head_material(low[1])[0];second_data=self._head_material(high[1])[0]
        first=first_data.get('face');second=second_data.get('face')
        visibility=(1-amount)*bool(first)+amount*bool(second)
        if data.get('face') and first and second:
            face=data['face'];fx,fy,fw,fh=face['box'];features={}
            for name in self.parts:
                if self.parts[name]['parent']!='features' and name not in ('mouth','nose'):continue
                a_name=self._eye_binding(name,view,low[1]);b_name=self._eye_binding(name,view,high[1])
                a=list(self._face_feature_rect(first,a_name));b=list(self._face_feature_rect(second,b_name))
                an=first_data.get('pivots',{}).get('head',self.pivots['head'])
                bn=second_data.get('pivots',{}).get('head',self.pivots['head'])
                selected_neck=data.get('pivots',{}).get('head',self.pivots['head'])
                a[0]-=an[0];a[1]-=an[1];b[0]-=bn[0];b[1]-=bn[1]
                xx,yy,ww,hh=[x+(y-x)*amount for x,y in zip(a,b)]
                xx+=selected_neck[0];yy+=selected_neck[1]
                xx=(xx-fx)/fw*230;yy=(yy-fy)/fh*150;ww=ww/fw*230;hh=hh/fh*150
                if face.get('flip'):xx=230-xx-ww
                original=face.get('features',{}).get(name,{})
                features[name]={**original,'source':original.get('source',name),'box':[xx,yy,ww,hh]}
            data={**data,'face':{**face,'features':features}};override=(data,images)
        neck=data.get('pivots',{}).get('head',self.pivots['head'])
        local=replace(pose,view=view,camera_angle=None,head_yaw=pose.head_yaw-offset,face_visibility=visibility,
                      transforms={**pose.transforms,'upper':{}})
        painter.save();current={**self.pivots,**self.rigs.get(pose.view,({},{}))[0].get('pivots',{})}
        self._joint(painter,'upper',pose,current)
        painter.translate(target_neck[0]-neck[0],target_neck[1]-neck[1])
        self._render_projected_head(painter,local,data or None,override)
        painter.restore()

    def _head_material(self,view):
        if view in self.head_frames:return self.head_frames[view]
        if view in self.rigs:return self.rigs[view]
        # The upstream quarter view already has genuine separate face, fringe,
        # horns and ears. Keep that original hierarchy as a head-only material.
        parts=[{**p,'z':p['z']*.6} for p in self.parts.values() if p['parent'] in ('head','hairFront','ahoge')]
        return {'parts':parts,'pivots':self.pivots,'face':{'box':[270,315,230,150]}},self.images

    def _face_feature_rect(self,face,name):
        original=self.parts[name]['box']
        x,y,w,h=face.get('features',{}).get(name,{}).get('box',[original[0]-270,original[1]-315,*original[2:]])
        if face.get('flip'):x=230-x-w
        fx,fy,fw,fh=face['box']
        return fx+x/230*fw,fy+y/150*fh,w/230*fw,h/150*fh

    def _eye_binding(self,name,source_view,target_view):
        def swapped(view):
            return view=='right' or self.puppet.get('headTurns',{}).get(view,{}).get('swapEyes',view.startswith('right'))
        if swapped(source_view)==swapped(target_view):return name
        if 'near' in name:return name.replace('near','far')
        if 'far' in name:return name.replace('far','near')
        return name

    def _arm_geometry(self,part,images,pose,pivots):
        spec=part['articulation'];node=part['parent'];side=0 if node=='armNear' else 1
        lift=pose.hands[side];point=pose.hands[2] if side==0 else 0.
        state=pose.transforms[node];root=pivots[node]
        shoulder=(root[0]+state.get('x',0),root[1]+state.get('y',0))
        sizes={k:(images[f'{part["id"]}#{k}'].width(),images[f'{part["id"]}#{k}'].height()) for k in ('upper','forearm','hand')}
        base=pose.arm_base.get(node,0. if pose.motion in HAND_GESTURES else state.get('a',0)*(1-max(lift,point)))
        chain=arm_chain(spec,sizes,shoulder,lift,point,pose.hands[3] if lift else 0.,base,part.get('flipX',False))
        hand=spec['segments']['point'];im=images[f'{part["id"]}#point'];w,h=im.width()*hand['scale'],im.height()*hand['scale']
        root=chain['hand']['root'];u,v=hand['rootUV'];mirror=part.get('flipX',False)
        aim={'box':[root[0]-(1-u if mirror else u)*w,root[1]-v*h,w,h],
             'flipX':mirror,'indexTipUV':hand['endUV'],'indexRay':hand['indexRay'],'target':list(pose.point_target or spec['pointTarget'])}
        if pose.point_target:
            matrix=QTransform();self._joint(matrix,'upper',pose,pivots)
            inverse,ok=matrix.inverted()
            if ok:
                target=inverse.map(QPointF(*pose.point_target));aim['target']=[target.x(),target.y()]
        aim['rotation']=self._aim_angle(aim,root,im.size())
        chain['point']=aim
        return chain

    def _render_arm(self,painter,part,images,pose,pivots):
        chain=self._arm_geometry(part,images,pose,pivots);spec=part['articulation']
        self._joint(painter,'upper',pose,pivots)
        point=pose.hands[2] if part['parent']=='armNear' else 0.
        names=('hand','point') if part.get('armSegment')=='hand' else (part['armSegment'],)
        for name in names:
            segment=chain[name];root=chain['hand']['root'] if name=='point' else segment['root']
            painter.save();painter.setOpacity(point if name=='point' else 1-point if name=='hand' else 1)
            painter.translate(*root);painter.rotate(segment['rotation']);painter.translate(-root[0],-root[1])
            x,y,w,h=segment['box']
            if segment.get('flipX'):
                painter.translate(x+w,y);painter.scale(-1,1);x=y=0
            self._draw_texture(painter,[x,y,w,h],images[f'{part["id"]}#{name}']);painter.restore()

    def _render_view(self, painter, pose, scope='all',rig_override=None):
        data, images = rig_override or self.rigs[pose.view]
        if scope=='all' and pose.look_back>0 and pose.view in ('back-left','back-right'):
            self._render_look_back(painter,pose,data)
            return
        pivots = {**self.pivots, **data.get("pivots", {})}
        layers = list(data['parts'])
        if self.puppet and pose.view in ('left','right') and scope in ('all','body','rear-base'):
            layers.append({'id':'@tail-foreground','parent':'tail','box':[0,0,1,1],'z':4.2,'tailRig':True,'foreground':True})
        # Dedicated painted palms/finger poses keep their natural proportions;
        # do not use sleeve length as the shoulder-to-hand lever.
        expanded=[]
        for part in layers:
            if part.get('articulation'):
                for segment,z in (('upper',part['z']),('forearm',19),('hand',19.1)):
                    expanded.append({**part,'armSegment':segment,'z':z})
                continue
            side="left" if part["parent"]=="armNear" else "right"
            active=(pose.motion in ("wave","raise-left","point","raise-both","dance") and side=="left") or (pose.motion in ("raise-right","raise-both","dance") and side=="right")
            kind="point" if pose.motion=="point" else "raised"
            variant=part.get("variants",{}).get(kind) if active else None
            if variant and pose.gesture>0:
                weight=smooth(pose.gesture)
                expanded.append({**part,"opacity":1-weight})
                angle=variant.get("startRotation",0)*(1-pose.gesture)+variant.get("rotation",0)*pose.gesture
                if pose.motion=="wave":angle+=math.sin(pose.phase*math.pi*12)*7*pose.gesture
                if pose.motion=="dance":angle+=math.sin(pose.phase*math.pi*8)*10*pose.gesture
                expanded.append({**variant,"id":f'{part["id"]}@{kind}',"parent":part["parent"],"z":19,"opacity":weight,"jointAngle":angle})
            else:
                expanded.append(part)
        layers=expanded
        face = data.get("face")
        if data.get("sourceNeck"):
            layers.append(dict(id="@neck",parent="upper",box=self.parts["neck"]["box"],z=7))
        if face:
            layers += [dict(id="@eyes", parent="head", box=face["box"], z=14),
                       dict(id="@lashes", parent="head", box=face["box"], z=18)]
        layers=[part for part in layers if self._in_scope(part,scope)]
        if scope=='all':
            layers=[part for part in layers if self._in_scope(part,'rear-base')]
            layers.append(dict(id='@projected-head',parent='head',box=[0,0,1,1],z=18))
        for part in sorted(layers, key=lambda p: p["z"]):
            painter.save()
            painter.setOpacity(part.get("opacity",1))
            if part['id']=='@projected-head':
                self._render_projected_head(painter,pose,data);painter.restore();continue
            if self.puppet and part.get('tailRig'):
                self._render_tail(painter,pose,part.get('foreground',False));painter.restore();continue
            if self.puppet and part.get('legRig'):
                self._render_leg(painter,part,images[part['id']],pose,pivots);painter.restore();continue
            if self.puppet and part.get('cloth'):
                self._render_garment(painter,part,images[part['id']],pose,pivots);painter.restore();continue
            if part.get('articulation'):
                self._render_arm(painter,part,images,pose,pivots);painter.restore()
                continue
            joint_pose=pose
            if "jointAngle" in part:
                node=part["parent"]
                joint_pose=replace(pose,transforms={**pose.transforms,node:{**pose.transforms[node],"a":part["jointAngle"]}})
            self._joint(painter, part["parent"], joint_pose, pivots)
            if part.get('restRotation'):
                x,y=pivots[part['parent']];painter.translate(x,y);painter.rotate(part['restRotation']);painter.translate(-x,-y)
            if part["id"] == "@neck":
                painter.drawImage(QRectF(*part["box"]),self.images["neck"])
            elif part["id"].startswith("@"):
                x,y,w,h = part["box"]
                painter.translate(x+w if face.get("flip") else x, y)
                if face.get("flip"):
                    painter.scale(-1, 1)
                face_pose = replace(pose, gaze=(-pose.gaze[0],pose.gaze[1])) if face.get("flip") else pose
                painter.setOpacity(painter.opacity()*pose.face_visibility)
                painted=self._face(face_pose,part["id"]=="@lashes",face.get("oneEye",False),face)
                if face.get("maskSkin"):
                    fp=QPainter(painted);fp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                    fp.drawImage(0,0,self._skin_mask(pose.view,data,images));fp.end()
                painter.drawImage(QRectF(0,0,w,h),painted)
            elif part.get("warpY"):
                x,y,w,h=part["box"]; a,b=part["warpY"]; im=images[part["id"]]
                painter.drawImage(QRectF(x,y,w,h*b),im,QRectF(0,0,im.width(),im.height()*a))
                painter.drawImage(QRectF(x,y+h*b,w,h*(1-b)),im,QRectF(0,im.height()*a,im.width(),im.height()*(1-a)))
            elif part.get("mesh"):
                if part.get("cutout"):
                    clip=QPainterPath(); clip.addRect(QRectF(0,0,1024,1024))
                    hole=QPainterPath(); hole.addEllipse(QRectF(*part["cutout"]))
                    painter.setClipPath(clip.subtracted(hole),Qt.ClipOperation.IntersectClip)
                self._mesh(painter,images[part["id"]],part["box"],pose.cloth if part.get('cloth') else pose.hair,part.get("warpStart",0))
            else:
                if part.get("flipX"):
                    x,y,w,h = part["box"]
                    painter.translate(x+w,y); painter.scale(-1,1)
                    self._draw_texture(painter,[0,0,w,h],images[part["id"]])
                else:
                    self._draw_texture(painter,part['box'],images[part["id"]])
            painter.restore()
        if scope=='front-head':self._head_accent(painter,pose,pivots)
