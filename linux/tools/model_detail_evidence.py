#!/usr/bin/env python3
"""Fixed-time evidence for the second repair pass, using the actual Qt renderer."""
import argparse
from pathlib import Path

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor,QGuiApplication,QImage,QPainter

from gpt_niang_linux.model.assets import model_directory
from gpt_niang_linux.model.motion import Animator
from gpt_niang_linux.model.render import DragonRenderer
from model_review_evidence import advance,panel,sheet


def labelled(image,label):
    image=image.copy();p=QPainter(image);p.fillRect(0,510,512,40,QColor('#dad5e5'))
    f=p.font();f.setPixelSize(22);p.setFont(f);p.setPen(QColor('#544467'))
    p.drawText(QPointF(80,535),label);p.end();return image


def frame(renderer,animator,label):
    image=QImage(512,550,QImage.Format.Format_RGB32);image.fill(QColor('#dad5e5'))
    p=QPainter(image);p.drawImage(0,0,renderer.render(animator.pose(),512));p.end()
    return labelled(image,label)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--previous',type=Path);args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    app=QGuiApplication([]);renderer=DragonRenderer(model_directory())
    if args.previous:
        gestures=QImage(str(args.previous/'fix-gestures-after.png'))
        rear=QImage(str(args.previous/'fix-look-back-after.png'))
        if gestures.isNull() or rear.isNull():raise ValueError('Missing previous fixed-time evidence')
        panels=[]
        for old,box,view,action,label in (
            (gestures,(512,550,512,550),'front','raise-both','举双手'),
            (gestures,(1024,550,512,550),'front','point','指向'),
            (rear,(512,0,512,550),'back-left','look-back','左后回眸'),
            (rear,(1536,0,512,550),'back-right','look-back','右后回眸')):
            panels.extend((labelled(old.copy(*box),label+' · 上轮'),panel(renderer,view,action,label+' · 本轮')))
        sheet(panels,4,args.out/'fix-detail-before-after.png')
    panels=[]
    for seconds in (0,.1,.2,.35,.65):
        a=Animator();a.set_view('front');a.play('raise-left');advance(a,seconds)
        panels.append(frame(renderer,a,f'抬手 {seconds:.2f}s'))
    for seconds in (0,.04,.08,.12,.18):
        a=Animator();a.set_view('front');a.play('raise-left');advance(a,.65);a.play('stand');advance(a,seconds)
        panels.append(frame(renderer,a,f'切换后 {seconds:.2f}s'))
    sheet(panels,5,args.out/'fix-arm-transition.png')
    panels=[]
    for view in ('back-left','back','back-right'):
        panels.append(panel(renderer,view))
    for view in ('back-left','back','back-right'):
        a=Animator();a.set_view(view);a.clock=1
        image=QImage(512,550,QImage.Format.Format_RGB32);image.fill(QColor('#dad5e5'))
        p=QPainter(image);p.setRenderHints(QPainter.RenderHint.Antialiasing|QPainter.RenderHint.SmoothPixmapTransform)
        pose=a.pose();p.scale(.4,.4);p.translate(150+pose.root_x,220+pose.root_y)
        renderer._render_view(p,pose,scope='body');p.end();panels.append(labelled(image,'去头发检查 · '+view))
    sheet(panels,3,args.out/'fix-rear-depth.png')
    print('Captured second-pass comparison, arm transition and rear body depth.')


if __name__=='__main__':main()
