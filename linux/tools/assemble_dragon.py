#!/usr/bin/env python3
"""Slice approved generated cutouts. No pixel painting or background removal.

Crop rectangles are curated against imagegen outputs; rejected torso/arm cells
are intentionally excluded. Re-run to reproduce the runtime atlas from sources.
"""
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBitmap, QGuiApplication, QImage, QRegion

ROOT = Path(__file__).resolve().parents[1]/'models/dragon'
# id, source crop (x,y,w,h), design box, parent joint, z
BACK = [
    ('leg-far', (65,775,260,300), [355,650,95,310], 'legFar', 0),
    ('leg-near', (400,775,265,300), [420,650,95,310], 'legNear', 1),
    ('hair-back', (380,0,348,510), [200,200,480,610], 'hairBack', 3),
    ('tail', (1070,490,378,290), [425,670,390,280], 'tail', 2),
    ('arm-far', (0,475,330,300), [285,478,105,200], 'armFar', 2.8),
    ('arm-near', (1210,65,238,375), [470,478,105,200], 'armNear', 2.9),
    ('wing-far', (330,490,360,245), [150,461,275,165], 'wingFar', 1.8),
    ('wing-near', (690,490,380,250), [450,461,290,165], 'wingNear', 1.9),
    ('head', (0,0,380,440), [225,65,420,410], 'head', 9),
]


def trimmed(image):
    bounds = QRegion(QBitmap.fromImage(image.createAlphaMask(Qt.ImageConversionFlag.ThresholdAlphaDither))).boundingRect()
    if bounds.isEmpty(): raise ValueError('Empty sprite')
    return image.copy(bounds)


LEFT = [
    ('head', (0,0,400,460), [225,65,370,420], 'head', 10),
    ('hair-back', (400,0,320,470), [280,180,390,610], 'hairBack', 0),
    ('dress', (725,30,435,430), [300,447,350,507], 'upper', 4),
    ('arm-near', (1180,50,260,400), [395,496,110,202], 'armNear', 8),
    ('arm-far', (50,470,270,300), [345,478,105,200], 'armFar', 3),
    ('wing-near', (385,480,325,250), [455,461,238,142], 'wingNear', 2),
    ('wing-far', (725,480,345,250), [370,461,150,142], 'wingFar', 1),
    ('tail', (1075,465,373,310), [450,640,393,297], 'tail', 1.5),
    ('leg-near', (65,780,260,295), [415,646,98,323], 'legNear', 2.6),
    ('leg-far', (400,780,260,295), [365,652,97,311], 'legFar', 2.5),
]


GENERIC_CROPS = {
    'head': (0,0,400,460), 'hair-back': (400,0,330,500),
    'dress': (730,25,435,475), 'arm-near': (1180,40,268,440),
    'arm-far': (0,480,330,294), 'wing-far': (330,480,370,270),
    'wing-near': (700,480,370,270), 'tail': (1080,480,368,290),
    'leg-near': (65,780,265,306), 'leg-far': (400,780,290,306),
    'hair-front': (730,780,340,306),
}


def skin_center(image, half=None):
    points = []
    for y in range(int(image.height()*.24)):
        for x in range(image.width()):
            if half == 'left' and x > image.width()/2: continue
            if half == 'right' and x <= image.width()/2: continue
            c = image.pixelColor(x,y)
            if c.alpha()>128 and c.red()>220 and c.green()<239 and c.blue()<247 and c.red()>c.green()+7 and c.red()>=c.blue()-2:
                points.append((x,y))
    if not points: return image.width()/2, image.height()*.08
    return sum(x for x,y in points)/len(points), sum(y for x,y in points)/len(points)


def generic(view, face=None):
    source = ROOT/f'source/{view}-parts.png'
    if not source.exists(): return None
    target = ROOT/view; target.mkdir(exist_ok=True)
    atlas = QImage(str(source))
    rear = view.startswith('back-')
    crops=dict(GENERIC_CROPS)
    if rear:
        crops['head']=(0,0,400,500); crops['dress']=(730,25,435,510)
    sprites = {key: trimmed(atlas.copy(*crop)) for key,crop in crops.items() if key != 'hair-front' or view == 'front'}
    if rear:
        for key in ('wing-far','wing-near','arm-far','arm-near','leg-far','leg-near'):
            sprites[key]=QImage(str(ROOT/f'back/{key}.png'))
    rightward = view in ('right','front-right','back-right')
    parts = []
    boxes = {
        'head': [225,65,420,475], 'hair-back': [200,180,480,610],
        'dress': [225,447,455,507], 'arm-near': [457,478,114,202],
        'arm-far': [292,478,117,185], 'wing-far': [150,461,275,165] if rear else [226,461,164,132],
        'wing-near': [450,461,290,165] if rear else [491,461,238,142],
        'tail': [125 if rightward else 500,640,393,297],
        'leg-far': [342,652,97,311], 'leg-near': [412,646,98,323],
        'hair-front': [225,145,420,350],
    }
    if view == 'right':
        boxes['hair-back'] = [200,180,390,610]
        boxes['dress'] = [300,447,350,507]
        boxes['leg-far'],boxes['leg-near']=[465,652,97,311],[480,646,98,323]
        boxes['wing-far'], boxes['wing-near'] = [330,461,170,142], [260,461,238,142]
    # Skin attachment centers align the independently generated sleeves to the
    # actual shoulder stumps, rather than assuming the old perspective's pivots.
    pivots = {}
    for arm,half in (('arm-far','left'),('arm-near','right')):
        body = sprites['dress']; bx,by,bw,bh = boxes['dress']
        cx,cy = skin_center(body, None if view == 'right' else half)
        ax,ay = skin_center(sprites[arm])
        px,py = bx+cx/body.width()*bw, by+cy/body.height()*bh
        aw,ah = boxes[arm][2:]
        boxes[arm][:2] = [px-ax/sprites[arm].width()*aw, py-ay/sprites[arm].height()*ah]
        pivots['armNear' if arm == 'arm-near' else 'armFar'] = [px,py]
    pivots['head']=[sum(pivots[n][0] for n in ('armNear','armFar'))/2,460]
    parents = {'head':'head','hair-back':'hairBack','dress':'upper','arm-near':'armNear','arm-far':'armFar',
               'wing-far':'wingFar','wing-near':'wingNear','tail':'tail','leg-far':'legFar','leg-near':'legNear','hair-front':'hairFront'}
    orders = {'hair-back':0,'wing-far':1,'wing-near':2,'tail':2.2,'leg-far':2.4,'leg-near':2.6,
              'arm-far':3,'dress':4,'arm-near':8,'head':10,'hair-front':16}
    for key,im in sprites.items():
        if key == 'hair-front' and view != 'front': continue
        if rear and key == 'hair-front': continue
        im.save(str(target/f'{key}.png'))
        spec=dict(id=key,src=f'{key}.png',box=boxes[key],parent=parents[key],z=orders[key],mesh=key in ('hair-back','hair-front'))
        if key == 'hair-front' and view == 'front': spec['cutout']=[520,250,100,100]
        if key == 'head' and not rear: spec['warpY']=[.73,.83]
        if rightward and key == 'tail': spec['flipX']=True
        if view == 'right' and key == 'wing-near': spec['flipX']=True
        parts.append(spec)
    rig = dict(schemaVersion=1,status='experimental',view=view,parts=parts,pivots=pivots)
    if face: rig['face']=face; rig['sourceNeck']=view == 'front'
    (target/'rig.json').write_text(json.dumps(rig,ensure_ascii=False,indent=2)+'\n')
    return {'rig':f'{view}/rig.json','status':'experimental'}


def main():
    app = QGuiApplication([])
    atlas = QImage(str(ROOT/'source/back-parts-draft.png'))
    parts = []
    for key, crop, box, parent, z in BACK:
        image = trimmed(atlas.copy(*crop))
        image.save(str(ROOT/f'back/{key}.png'))
        parts.append(dict(id=key, src=f'{key}.png', box=box, parent=parent, z=z, mesh=parent == 'hairBack'))
    image = trimmed(QImage(str(ROOT/'source/back-dress.png')))
    image.save(str(ROOT/'back/dress.png'))
    parts.append(dict(id='dress', src='dress.png', box=[225,447,455,507], parent='upper', z=2.5))
    rig = dict(schemaVersion=1, status='experimental', view='back', source='../source/back-parts-draft.png',
               sourceBody='../source/back-dress.png', parts=parts, pivots={'armFar': [355,484], 'armNear': [485,484]})
    (ROOT/'back/rig.json').write_text(json.dumps(rig, ensure_ascii=False, indent=2)+'\n')
    (ROOT/'left').mkdir(exist_ok=True)
    atlas = QImage(str(ROOT/'source/left-parts-draft.png'))
    parts = []
    for key, crop, box, parent, z in LEFT:
        trimmed(atlas.copy(*crop)).save(str(ROOT/f'left/{key}.png'))
        parts.append(dict(id=key, src=f'{key}.png', box=box, parent=parent, z=z, mesh=parent == 'hairBack'))
    rig = dict(schemaVersion=1, status='experimental', view='left', parts=parts,
               pivots={'armFar': [390,484], 'armNear': [440,505], 'wingNear': [460,520], 'wingFar': [490,520]})
    (ROOT/'left/rig.json').write_text(json.dumps(rig, ensure_ascii=False, indent=2)+'\n')
    head_source = QImage(str(ROOT/'source/left-head-parts.png'))
    if not head_source.isNull():
        trimmed(head_source.copy(0,0,head_source.width(),870)).save(str(ROOT/'left/head.png'))
        rig['face'] = dict(box=[231,315,138,150],oneEye=True)
        rig['sourceNeck']=False
        next(p for p in rig['parts'] if p['id']=='head')['box'][3]=475
        next(p for p in rig['parts'] if p['id']=='head')['warpY']=[.73,.83]
        (ROOT/'left/rig.json').write_text(json.dumps(rig,ensure_ascii=False,indent=2)+'\n')
    views = {'back': {'rig':'back/rig.json','status':'experimental'}, 'left': {'rig':'left/rig.json','status':'experimental'}}
    configs = {'front': dict(box=[312,315,230,150]), 'right':dict(box=[509,315,138,150],oneEye=True,flip=True),
               'front-right':dict(box=[455,315,160,150],flip=True), 'back-left':None,'back-right':None}
    for view,face in configs.items():
        spec = generic(view, face)
        if spec: views[view]=spec
    (ROOT/'views.json').write_text(json.dumps({'schemaVersion':1,'views':views},indent=2)+'\n')


if __name__ == '__main__': main()
