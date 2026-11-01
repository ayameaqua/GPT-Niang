#!/usr/bin/env python3
"""Capture the repaired model at fixed scales/times; never paints character art."""
import argparse
import hashlib
import json
from pathlib import Path

from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QColor,QGuiApplication,QImage,QPainter

from gpt_niang_linux.model.assets import model_directory
from gpt_niang_linux.model.motion import Animator,MOTIONS,VIEWS
from gpt_niang_linux.model.render import DragonRenderer

LINUX=Path(__file__).resolve().parents[1]


def advance(a,seconds):
    for _ in range(round(seconds*100)):a.advance(.01)


def panel(renderer,view,action='',label=''):
    a=Animator();a.set_view(view)
    if action:a.play(action);advance(a,1 if action=='look-back' else .6)
    else:a.clock=1
    image=QImage(512,550,QImage.Format.Format_RGB32);image.fill(QColor('#dad5e5'))
    p=QPainter(image);p.drawImage(0,0,renderer.render(a.pose(),512))
    f=p.font();f.setPixelSize(22);p.setFont(f);p.setPen(QColor('#544467'))
    p.drawText(QPointF(160,535),label or VIEWS[a.view]);p.end()
    return image


def sheet(panels,columns,path):
    out=QImage(columns*512,((len(panels)+columns-1)//columns)*550,QImage.Format.Format_RGB32)
    out.fill(QColor('#dad5e5'));p=QPainter(out)
    for i,item in enumerate(panels):p.drawImage((i%columns)*512,(i//columns)*550,item)
    p.end();out.save(str(path))


def check_bounds(renderer):
    clipped=[];empty=[];samples=0
    for view in VIEWS:
        for action,(_,duration) in MOTIONS.items():
            a=Animator();a.set_view(view);a.play(action)
            for _ in range(120):
                if not a.pending:break
                a.advance(.01)
            for fraction in (0,.25,.5,.75,.99):
                while a.action==action and a.elapsed+1e-8<duration*fraction:a.advance(.01)
                frame=renderer.render(a.pose(),320).convertToFormat(QImage.Format.Format_RGBA8888)
                alpha=bytes(frame.constBits())[3::4];edge=alpha[:320]+alpha[-320:]+alpha[::320]+alpha[319::320]
                samples+=1
                if max(edge)>16:clipped.append([view,action,fraction,max(edge)])
                if max(alpha)==0:empty.append([view,action,fraction])
    return {'samples':samples,'phases':[0,.25,.5,.75,.99],'initialViews':len(VIEWS),'actions':len(MOTIONS),
            'clipped':clipped,'empty':empty,'scope':'neutral expression; canvas bounds only, not visual acceptance'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--check-bounds',action='store_true');args=parser.parse_args()
    app=QGuiApplication([]);renderer=DragonRenderer(model_directory());args.out.mkdir(parents=True,exist_ok=True)
    before=QImage(str(args.out/'fix-before-front.png'))
    if not before.isNull():
        after=panel(renderer,'front')
        result=QImage(1024,590,QImage.Format.Format_RGB32);result.fill(QColor('#dad5e5'));p=QPainter(result)
        p.drawImage(0,40,before);p.drawImage(512,40,after)
        f=p.font();f.setPixelSize(24);p.setFont(f);p.setPen(QColor('#544467'))
        p.drawText(QPointF(215,29),'修前');p.drawText(QPointF(727,29),'修后');p.end()
        result.save(str(args.out/'fix-front-before-after.png'))
    sheet([panel(renderer,'front',action,label) for action,label in (
        ('','待机'),('wave','招手'),('raise-left','抬左手'),('raise-right','抬右手'),('raise-both','举双手'),('point','指向锚点'))],3,args.out/'fix-gestures-after.png')
    sheet([panel(renderer,v,a,label) for v,a,label in (
        ('back-left','','左后侧'),('back-left','look-back','左后侧回眸'),
        ('back-right','','右后侧'),('back-right','look-back','右后侧回眸'))],4,args.out/'fix-look-back-after.png')
    evidence={str(p.relative_to(args.out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.glob('fix-*.png')}
    sources=[* (LINUX/'gpt_niang_linux/model').glob('*.py'),LINUX/'models/dragon/asset-hashes.json']
    snapshot={'beforeRuntimeCommit':'a219dc3aea9eb444349fb23e85a5072b6a739e2e',
              'renderedEvidence':evidence,'implementation':{str(p.relative_to(LINUX)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
              'scope':'fixed-time Qt compositions; staged visual comparisons, not exhaustive acceptance'}
    if args.check_bounds:snapshot['bounds']=check_bounds(renderer)
    (args.out/'fix-snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(snapshot.get('bounds',{'evidence':len(evidence)})))


if __name__=='__main__':main()
