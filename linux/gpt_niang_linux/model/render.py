"""Qt raster compositor with hierarchical joints and continuous texture warps.

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
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPolygonF

from .assets import validate_model
from .motion import smooth
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
        self.face_masks = {}
        self.extension_directory = LINUX_ROOT / "models/dragon"
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
            images[part["id"]] = im
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
            cx, cy = x+w/2, y+h/2
            closed = pose.eye_closed or face in ("happy", "cry", "flustered") or (face == "wink" and index == 0)
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
            elif closed:
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
                    ep.drawImage(QRectF(ix-x+gaze_x*5, iy-y+gaze_y*4, iw, ih), feature(f"eye-{side}-iris"))
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
        if not lashes:
            if face in ("shy", "love", "flustered"):
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(235, 143, 169, 85))
                blush = layout.get("blush", [[37,101,26,9],[164,101,26,9]])
                for index, (x,y,w,h) in enumerate(blush):
                    if not one_eye or index == 1:
                        painter.drawEllipse(QRectF(270+x,315+y,w,h))
            mx,my,mw,mh = features["mouth"]["box"]
            mouth_x,mouth_y = mx+mw/2,my+mh/2
            if pose.speech > .05 or face in ("surprised", "scared", "pout", "sleepy", "cry"):
                painter.setPen(QPen(INK, 1.5))
                painter.setBrush(QColor("#aa6f85"))
                height = 3 + pose.speech*8 + (5 if face in ("surprised", "cry") else 0)
                painter.drawEllipse(QRectF(mouth_x-3.5, mouth_y-height/2, 7+pose.speech*3, height))
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
                    yy=315+y+(0 if face == "cry" else 3+(pose.time*25 % 25))
                    painter.drawRoundedRect(QRectF(270+x, yy, 7, 30 if face == "cry" else 10), 3, 3)
        painter.end()
        return image

    def _skin_mask(self, view, data, images):
        """Keep facial overlays on the painted skin, behind baked hair strands."""
        if view in self.face_masks:
            return self.face_masks[view]
        part=next(p for p in data["parts"] if p["id"]=="head")
        head=images["head"].convertToFormat(QImage.Format.Format_RGBA8888)
        rgba=bytes(head.constBits()); pixels=bytearray(len(rgba))
        for i in range(0,len(rgba),4):
            r,g,b,a=rgba[i:i+4]
            if a and r>=225 and g>=195 and r>=g+2 and r>=b+3:
                pixels[i:i+4]=bytes((255,255,255,a))
        skin=QImage(pixels,head.width(),head.height(),head.bytesPerLine(),QImage.Format.Format_RGBA8888).copy()
        mask=QImage(230,150,QImage.Format.Format_ARGB32_Premultiplied);mask.fill(Qt.GlobalColor.transparent)
        mp=QPainter(mask);mp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        x,y,w,h=data["face"]["box"]
        mp.scale(230/w,150/h);mp.translate(-x,-y)
        mp.drawImage(QRectF(*part["box"]),skin);mp.end()
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
        if pose.blend_view and pose.view_mix>0:
            first=self.render(replace(pose,blend_view="",view_mix=0),width,height,debug)
            second=self.render(replace(pose,view=pose.blend_view,blend_view="",view_mix=0),width,height,debug)
            return self._mix(first,second,pose.view_mix)
        image = QImage(max(1, int(width)), max(1, int(height)), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        painter.scale(width/DESIGN_SIZE, height/DESIGN_SIZE)
        painter.translate(150+pose.root_x, 220+pose.root_y)
        painter.translate(425, 969)
        painter.rotate(pose.root_angle)
        painter.translate(-425, -969)
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

    @staticmethod
    def _in_scope(part,scope):
        head=part['parent'] in ('head','hairBack','hairFront','ahoge')
        if scope=='back-hair':return part['parent']=='hairBack'
        if scope=='front-head':return head and part['parent']!='hairBack'
        return scope=='all' or head==(scope=='head')

    def _render_source(self, painter, pose, scope='all'):
        layers = [(part["z"], name, part) for name, part in self.parts.items()
                  if part["parent"] != "features" and name != "nose"]
        layers += [(20.5, "@eyes", {"parent": "head", "box": [270, 315, 230, 150]}),
                   (27.5, "@lashes", {"parent": "head", "box": [270, 315, 230, 150]})]
        layers=[layer for layer in layers if self._in_scope(layer[2],scope)]
        for _, name, part in sorted(layers, key=lambda p: p[0]):
            painter.save()
            seated=smooth(pose.seat)
            if name == "sit":
                painter.setOpacity(seated)
            elif name in ("tail","leg-far","leg-near","skirt-far","skirt-near","apron","wing-far","wing-near"):
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
        if scope in ('body','back-hair'):return
        painter.save()
        self._joint(painter, "head", pose)
        painter.setPen(QPen(QColor("#8c76b7"), 3))
        font = painter.font()
        font.setPixelSize(48)
        painter.setFont(font)
        accent = {"confused": "?", "surprised": "!", "thinking": "···", "worried": "◦", "angry": "♯"}.get(pose.expression, "")
        if pose.eye_closed:
            accent = "z"
        painter.drawText(QPointF(565, 220+math.sin(pose.time*2)*3), accent)
        painter.restore()

    def _render_look_back(self,painter,pose,data):
        """Keep the rear-quarter body while the head turns over its shoulder."""
        current={**self.pivots,**data.get('pivots',{})}
        target='front-left' if pose.view=='back-left' else 'front-right'
        reference={**self.pivots,**self.rigs.get(target,({},{}))[0].get('pivots',{})}
        layers=[]
        for view in (pose.view,target):
            layer=QImage(painter.device().width(),painter.device().height(),QImage.Format.Format_ARGB32_Premultiplied)
            layer.fill(Qt.GlobalColor.transparent)
            hp=QPainter(layer);hp.setRenderHints(painter.renderHints());hp.setWorldTransform(painter.worldTransform())
            head_pose=replace(pose,view=view,look_back=0)
            if view==target:
                def reference_head(scope):
                    hp.save();self._joint(hp,'upper',pose,current)
                    hp.translate(current['head'][0]-reference['head'][0],current['head'][1]-reference['head'][1])
                    local=replace(head_pose,transforms={**pose.transforms,'upper':{}})
                    if view in self.rigs:self._render_view(hp,local,scope=scope)
                    else:self._render_source(hp,local,scope=scope)
                    hp.restore()
                # Preserve the source hair's ownership of depth. Its opaque
                # lavender underpaint belongs behind clothes, never over them.
                reference_head('back-hair')
                self._render_view(hp,replace(pose,look_back=0),scope='body')
                reference_head('front-head')
            else:
                self._render_view(hp,head_pose)
            hp.end();layers.append(layer)
        painter.save();painter.resetTransform()
        painter.drawImage(0,0,self._mix(*layers,pose.look_back));painter.restore()

    def _render_view(self, painter, pose, scope='all'):
        data, images = self.rigs[pose.view]
        if scope=='all' and pose.look_back>0 and pose.view in ('back-left','back-right'):
            self._render_look_back(painter,pose,data)
            return
        pivots = {**self.pivots, **data.get("pivots", {})}
        layers = list(data["parts"])
        # Dedicated painted palms/finger poses keep their natural proportions;
        # do not use sleeve length as the shoulder-to-hand lever.
        expanded=[]
        for part in layers:
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
        for part in sorted(layers, key=lambda p: p["z"]):
            painter.save()
            painter.setOpacity(part.get("opacity",1))
            joint_pose=pose
            if "jointAngle" in part:
                node=part["parent"]
                joint_pose=replace(pose,transforms={**pose.transforms,node:{**pose.transforms[node],"a":part["jointAngle"]}})
            self._joint(painter, part["parent"], joint_pose, pivots)
            if part["id"] == "@neck":
                painter.drawImage(QRectF(*part["box"]),self.images["neck"])
            elif part["id"].startswith("@"):
                x,y,w,h = part["box"]
                painter.translate(x+w if face.get("flip") else x, y)
                if face.get("flip"):
                    painter.scale(-1, 1)
                face_pose = replace(pose, gaze=(-pose.gaze[0],pose.gaze[1])) if face.get("flip") else pose
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
                    painter.drawImage(QRectF(0,0,w,h), images[part["id"]])
                else:
                    painter.drawImage(QRectF(*part["box"]), images[part["id"]])
            painter.restore()
