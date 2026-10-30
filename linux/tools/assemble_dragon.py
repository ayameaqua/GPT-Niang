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
    (ROOT/'views.json').write_text(json.dumps({'schemaVersion': 1, 'views': {
        'back': {'rig': 'back/rig.json', 'status': 'experimental'},
        'left': {'rig': 'left/rig.json', 'status': 'experimental'}}}, indent=2)+'\n')


if __name__ == '__main__': main()
