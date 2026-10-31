"""Connected joints, gesture replacement and small-window raster regressions."""
import json
import math
from pathlib import Path
import unittest

from PySide6.QtGui import QColor,QGuiApplication,QImage,QPainter

from gpt_niang_linux.model.articulation import arm_chain
from gpt_niang_linux.model.motion import Animator
from gpt_niang_linux.model.render import DragonRenderer

app=QGuiApplication.instance() or QGuiApplication([])
ROOT=Path(__file__).parents[1]/'models/dragon'


def advance(a,seconds):
    for _ in range(round(seconds*100)):a.advance(.01)


class ArmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rig=json.loads((ROOT/'rig-layouts.json').read_text())['views']['front']
        cls.arm=next(p for p in rig['parts'] if p['id']=='arm-near')['articulation']
        cls.sizes={name:(QImage(str(ROOT/'front'/s['src'])).width(),QImage(str(ROOT/'front'/s['src'])).height())
                   for name,s in cls.arm['segments'].items()}

    def test_elbow_and_wrist_remain_connected_at_constant_bone_lengths(self):
        for mirror in (False,True):
            for step in range(21):
                lift=step/20
                chain=arm_chain(self.arm,self.sizes,(498,504),lift,point=lift*.5,sway=9,mirror=mirror)
                self.assertEqual(chain['upper']['end'],chain['forearm']['root'])
                self.assertEqual(chain['forearm']['end'],chain['hand']['root'])
                for name,node in chain.items():
                    spec=self.arm['segments'][name];w,h=self.sizes[name]
                    expected=math.hypot((spec['endUV'][0]-spec['rootUV'][0])*w,(spec['endUV'][1]-spec['rootUV'][1])*h)*spec['scale']
                    self.assertAlmostEqual(math.dist(node['root'],node['end']),expected)

    def test_individual_limb_mirroring_preserves_anatomical_symmetry(self):
        for lift in (0,.2,.7,1):
            left=arm_chain(self.arm,self.sizes,(498,504),lift,sway=6)
            right=arm_chain(self.arm,self.sizes,(352,504),lift,sway=6,mirror=True)
            for name in left:
                self.assertAlmostEqual(left[name]['end'][0]+right[name]['end'][0],850)
                self.assertAlmostEqual(left[name]['end'][1],right[name]['end'][1])

    def test_wrist_wave_does_not_sweep_the_upper_arm_or_elbow(self):
        first=arm_chain(self.arm,self.sizes,(498,504),1,sway=-12)
        second=arm_chain(self.arm,self.sizes,(498,504),1,sway=12)
        for name in ('upper','forearm'):self.assertEqual(first[name],second[name])
        self.assertEqual(first['hand']['root'],second['hand']['root'])
        self.assertNotEqual(first['hand']['end'],second['hand']['end'])

    def test_replacement_and_cancel_retain_hand_channels_then_settle(self):
        for next_action in ('stand','carried','point','raise-right','turn',None):
            a=Animator();a.set_view('front');a.play('raise-both');advance(a,.23)
            before=a.pose().hands
            if next_action:a.play(next_action)
            else:a.cancel()
            self.assertEqual(a.pose().hands,before,next_action)
            advance(a,.2)
            if next_action in ('stand','carried','turn',None):self.assertEqual(a.pose().hands,(0,0,0,0))

    def test_repeated_gesture_does_not_snap_back_to_idle(self):
        a=Animator();a.set_view('front');a.play('wave');advance(a,.6)
        before=a.pose().hands;a.play('wave')
        self.assertEqual(a.pose().hands,before)
        advance(a,.01)
        self.assertLess(abs(a.pose().hands[0]-before[0]),.02)


class RasterDepthTests(unittest.TestCase):
    def test_small_sleeve_uses_area_filtering_instead_of_aliasing(self):
        source=QImage(64,64,QImage.Format.Format_ARGB32_Premultiplied);source.fill(QColor('white'))
        for x in range(0,64,4):
            for y in range(64):source.setPixelColor(x,y,QColor('black'))
        output=QImage(2,2,QImage.Format.Format_ARGB32_Premultiplied);output.fill(QColor('transparent'))
        r=DragonRenderer.__new__(DragonRenderer);r.texture_cache={};p=QPainter(output)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r._draw_texture(p,[0,0,2,2],source);p.end()
        for x in range(2):
            for y in range(2):
                self.assertAlmostEqual(output.pixelColor(x,y).red(),191,delta=2)
                self.assertEqual(output.pixelColor(x,y).alpha(),255)

    def test_head_region_feathers_into_long_hair_without_cutting_source(self):
        source=QImage(100,100,QImage.Format.Format_ARGB32_Premultiplied);source.fill(QColor('white'))
        cap=DragonRenderer._region_image(source,{'fadeBottom':[.54,.60]})
        lower=DragonRenderer._region_image(source,{'sourceWindow':[0,.49,1,.51]})
        self.assertEqual(cap.pixelColor(20,40).alpha(),255)
        self.assertEqual(cap.pixelColor(20,80).alpha(),0)
        self.assertGreater(cap.pixelColor(20,57).alpha(),0)
        self.assertEqual(lower.pixelColor(20,40).alpha(),0)
        self.assertEqual(lower.pixelColor(20,57).alpha(),255)
        self.assertEqual(source.pixelColor(20,80).alpha(),255)

    def test_invalid_depth_region_is_rejected(self):
        image=QImage(4,4,QImage.Format.Format_ARGB32)
        for spec in ({'sourceWindow':[0,.8,1,.5]},{'fadeBottom':[.6,.5]},{'sourceWindow':[0,0,1,float('nan')]}):
            with self.assertRaises(ValueError):DragonRenderer._region_image(image,spec)


if __name__=='__main__':unittest.main()
