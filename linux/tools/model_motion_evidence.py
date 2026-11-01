#!/usr/bin/env python3
"""Capture actual skeletal performances and warm render+input-mask timings."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time

from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QBitmap,QColor,QGuiApplication,QImage,QPainter,QRegion

from gpt_niang_linux.model.assets import model_directory
from gpt_niang_linux.model.motion import Animator,VIEWS
from gpt_niang_linux.model.render import DragonRenderer

LINUX=Path(__file__).resolve().parents[1]


def advance(animator,seconds):
    while seconds>1e-9:
        delta=min(.01,seconds);animator.advance(delta);seconds-=delta


def actor(view,action):
    animator=Animator();animator.set_view(view);animator.play(action)
    return animator


def panel(renderer,animator,label,size=384):
    image=QImage(size,size+36,QImage.Format.Format_RGB32);image.fill(QColor('#dad5e5'))
    painter=QPainter(image);painter.drawImage(0,0,renderer.render(animator.pose(),size))
    font=painter.font();font.setPixelSize(17);painter.setFont(font);painter.setPen(QColor('#483852'))
    painter.drawText(QPointF(18,size+24),label);painter.end();return image


def contact(panels,columns,path):
    width,height=panels[0].width(),panels[0].height()
    image=QImage(width*columns,height*((len(panels)+columns-1)//columns),QImage.Format.Format_RGB32)
    image.fill(QColor('#dad5e5'));painter=QPainter(image)
    for index,item in enumerate(panels):painter.drawImage(index%columns*width,index//columns*height,item)
    painter.end();image.save(str(path))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--animation',action='store_true');args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    app=QGuiApplication([]);renderer=DragonRenderer(model_directory())
    native=[]
    for view in VIEWS:
        animator=Animator();animator.set_view(view);animator.clock=1.
        native.append(panel(renderer,animator,view))
    contact(native,4,args.out/'native-8.png')
    for view,action in (('front','nod'),('left','nod'),('front','jump'),('left','jump'),('back-left','sit'),('back','sit'),('back-right','sit')):
        times=(0,.2,.6,1.1) if action!='sit' else (0,.2,.5,.9)
        panels=[]
        for seconds in times:
            animator=actor(view,action);advance(animator,seconds)
            panels.append(panel(renderer,animator,f'{animator.pose().view} / {action} / {seconds:.2f}s'))
        contact(panels,4,args.out/f'{view}-{action}.png')
    timings={}
    for view,action in (('front','nod'),('left','jump'),('back','run'),('back-left','sit'),('front-left','spin')):
        animator=actor(view,action);renderer.render(animator.pose(),384);samples=[]
        for _ in range(40):
            animator.advance(.02);start=time.perf_counter();frame=renderer.render(animator.pose(),384)
            QRegion(QBitmap.fromImage(frame.createAlphaMask(Qt.ImageConversionFlag.ThresholdAlphaDither)))
            samples.append((time.perf_counter()-start)*1000)
        timings[f'{view}/{action}']={'meanMs':round(statistics.mean(samples),2),'maxMs':round(max(samples),2),'frames':len(samples)}
    if args.animation:
        frames=args.out/'frames';frames.mkdir(exist_ok=True)
        actors=[actor('front','nod'),actor('left','jump'),actor('front-left','sit')]
        for index in range(144):
            phase=index%72
            if phase==36:actors[2].play('stand')
            if phase==0 and index:
                actors=[actor('front','nod'),actor('left','jump'),actor('front-left','sit')]
            contact([panel(renderer,a,label) for a,label in zip(actors,('head pitch','crouch / flight / landing','tail / seated pelvis'))],3,frames/f'{index:04d}.png')
            for animator in actors:animator.advance(1/30)
    sources=[* (LINUX/'gpt_niang_linux/model').glob('*.py'),LINUX/'models/dragon/asset-hashes.json']
    result={'size':384,'warmRenderAndInputMask':timings,'scope':'fixed-time actual Qt frames; limited direction-frame turns; not exhaustive visual acceptance',
            'implementation':{str(p.relative_to(LINUX)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'images':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.glob('*.png')}}
    (args.out/'motion-snapshot.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(timings))


if __name__=='__main__':main()
