"""Regressions demonstrated by the model review, using geometry fixtures."""
import math
import json
from pathlib import Path
import tempfile
import unittest

from PySide6.QtGui import QColor,QGuiApplication,QImage

from gpt_niang_linux.model.extraction import Atlas
from gpt_niang_linux.model.motion import Animator
from gpt_niang_linux.model.render import DragonRenderer
from unittest.mock import patch

app=QGuiApplication.instance() or QGuiApplication([])


def advance(animator,seconds):
    for _ in range(round(seconds*100)):
        animator.advance(.01)


class ExtractionTests(unittest.TestCase):
    def test_locator_does_not_clip_subject_or_include_inside_neighbor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixture.png'
            image=QImage(24,24,QImage.Format.Format_RGBA8888);image.fill(QColor(0,0,0,0))
            for y in range(2,15):
                for x in range(2,15):
                    if x<5 or x>11 or y>11:
                        image.setPixelColor(x,y,QColor(230,200,250,255))
            for y in range(6,8):
                for x in range(7,9):image.setPixelColor(x,y,QColor(0,0,0,255))
            image.setPixelColor(1,3,QColor(130,100,180,64))
            image.save(str(path));out,meta=Atlas(path).extract([2,2,2,3])
            x0,y0,_,_=meta['sourceBounds']
            self.assertEqual(out.pixelColor(3-x0,14-y0).alpha(),255)
            self.assertEqual(out.pixelColor(7-x0,6-y0).alpha(),0)
            self.assertEqual(out.pixelColor(1-x0,3-y0),image.pixelColor(1,3))

    def test_explicit_detached_detail_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixture.png'
            image=QImage(32,24,QImage.Format.Format_RGBA8888);image.fill(QColor(0,0,0,0))
            for x0 in (2,20):
                for y in range(2,10):
                    for x in range(x0,x0+4):image.setPixelColor(x,y,QColor('white'))
            image.save(str(path));atlas=Atlas(path)
            _,single=atlas.extract([2,2,4,8]);out,both=atlas.extract([2,2,4,8],[[20,2,4,8]])
            self.assertGreater(out.width(),single['outputSize'][0])
            self.assertEqual(len(both['selectedComponents']),2)


class ReviewedMotionTests(unittest.TestCase):
    def test_expression_does_not_replace_active_hand_gesture(self):
        neutral=Animator();neutral.set_view('front');neutral.play('raise-both');advance(neutral,.6)
        for expression in ('angry','scared'):
            a=Animator();a.set_view('front');a.set_expression(expression);a.play('raise-both');advance(a,.6)
            for node in ('armNear','armFar'):
                self.assertEqual(a.pose().transforms[node]['a'],neutral.pose().transforms[node]['a'])

    def test_carried_height_and_limbs_hold_then_release(self):
        a=Animator();a.play('carried');advance(a,.4)
        self.assertEqual(a.carry,1)
        advance(a,8)
        self.assertEqual(a.carry,1)
        self.assertLess(a.pose().root_y,-28)
        self.assertEqual(a.pose().transforms['armNear']['a'],-80)
        a.play('land');advance(a,.3)
        self.assertEqual(a.carry,0)
        a.cancel();self.assertEqual(a.carry,0)

    def test_landing_impulse_reaches_original_hair_warp(self):
        a=Animator();a.play('land');advance(a,.2);p=a.pose()
        self.assertEqual(p.transforms['hairBack']['warp'],p.hair)
        self.assertNotAlmostEqual(p.hair,math.sin(a.clock*1.7)*3)

    def test_profile_lean_follows_facing_and_frontal_has_no_roll(self):
        for view,sign in [('left',-1),('right',1)]:
            a=Animator();a.set_view(view);a.play('run');advance(a,3)
            self.assertGreater(a.pose().transforms['upper']['a']*sign,5)
            a.play('bow');advance(a,.7)
            self.assertGreater(a.pose().transforms['upper']['a']*sign,10)
        a=Animator();a.set_view('front');a.play('run');advance(a,3)
        self.assertEqual(a.pose().transforms['upper'].get('a',0),0)

    def test_frontal_walk_lifts_feet_instead_of_kicking_sideways(self):
        a=Animator();a.set_view('front');a.play('walk');advance(a,3)
        p=a.pose()
        self.assertTrue(any(p.transforms[n].get('sy',1)<.999 for n in ('legFar','legNear')))
        self.assertTrue(all(abs(p.transforms[n]['a'])<=1.5 for n in ('legFar','legNear')))

    def test_rear_expression_turns_but_profile_expression_keeps_its_view(self):
        a=Animator();a.set_view('right');a.set_expression('happy')
        self.assertEqual(a.view,'right');self.assertFalse(a.action)
        a.set_view('back');a.set_expression('happy')
        self.assertEqual(a.view,'back');self.assertEqual(a.action,'turn')
        advance(a,.4);self.assertEqual(a.view,'front-left')

    def test_turn_has_a_continuous_blend_between_registered_views(self):
        a=Animator();a.set_view('front');a.play('turn');advance(a,.05)
        p=a.pose();self.assertEqual(p.view,'front');self.assertEqual(p.blend_view,'front-left')
        self.assertGreater(p.view_mix,0);self.assertLess(p.view_mix,1)

    def test_look_back_turns_only_the_head_on_a_rear_quarter_body(self):
        a=Animator();a.set_view('back-right');a.play('look-back');advance(a,1)
        self.assertEqual(a.view,'back-right');self.assertGreater(a.pose().look_back,.99)
        before=a.pose().look_back;a.play('stand');self.assertEqual(a.pose().look_back,before)
        advance(a,.2);self.assertEqual(a.pose().look_back,0)

    def test_facing_request_during_turn_or_spin_is_consumed_at_the_end(self):
        for start in ('front','back'):
            for action in ('turn','spin'):
                a=Animator();a.set_view(start);a.play(action);advance(a,.12)
                a.set_expression('happy');advance(a,2)
                self.assertIn(a.view,('front','front-left','front-right','left','right'))
                self.assertFalse(a.face_requested)

    def test_interrupting_turn_preserves_the_visible_blend(self):
        a=Animator();a.set_view('front');a.play('turn');advance(a,.08)
        before=a.pose();a.play('stand');after=a.pose()
        self.assertEqual((before.view,before.blend_view,before.view_mix),(after.view,after.blend_view,after.view_mix))
        advance(a,.2);self.assertFalse(a.settling)
        self.assertEqual(a.view,'front-left')


class BindingTests(unittest.TestCase):
    def test_recorded_source_roots_project_to_their_joints(self):
        root=Path(__file__).parents[1]/'models/dragon'
        layouts=json.loads((root/'rig-layouts.json').read_text())
        for view,rig in layouts['views'].items():
            parts={p['id']:p for p in rig['parts']}
            for name,uv in rig.get('landmarks',{}).items():
                if name not in parts:continue
                p=parts[name];u,v=uv
                if p.get('flipX'):u=1-u
                if p.get('warpY'):
                    a,b=p['warpY'];v=v/a*b if v<=a else b+(v-a)/(1-a)*(1-b)
                x,y,w,h=p['box'];actual=[x+u*w,y+v*h];expected=rig['pivots'][p['parent']]
                for i in (0,1):self.assertAlmostEqual(actual[i],expected[i],delta=.02,msg=f'{view}/{name}')

    def test_turn_blend_keeps_opaque_overlap_opaque(self):
        # Feed two real render calls the same opaque fixture, checking the middle
        # of the composition. Endpoints alone did not catch the old 191 alpha.
        renderer=DragonRenderer.__new__(DragonRenderer);renderer.rigs={'front':None,'front-left':None}
        def solid(painter,pose):painter.fillRect(-500,-500,2500,2500,QColor('white'))
        with patch.object(renderer,'_render_view',side_effect=solid):
            a=Animator();a.set_view('front');a.play('turn');advance(a,.05)
            im=renderer.render(a.pose(),16)
        self.assertGreaterEqual(im.pixelColor(8,8).alpha(),254)

    def test_emotion_limbs_are_continuous_at_action_start_and_end(self):
        a=Animator();a.set_expression('angry');advance(a,.3)
        before=a.pose().transforms;a.play('stand');after=a.pose().transforms
        for node in ('armNear','armFar'):
            self.assertEqual(before[node]['a'],after[node]['a'])
        advance(a,1.19);before=a.pose().transforms;advance(a,.01);after=a.pose().transforms
        for node in ('armNear','armFar'):
            self.assertLess(abs(before[node]['a']-after[node]['a']),.2)

    def test_face_request_survives_replacement_with_persistent_action(self):
        a=Animator();a.set_view('back');a.play('spin');advance(a,.03)
        a.set_expression('happy');a.play('carried');advance(a,2)
        self.assertEqual(a.action,'carried');self.assertEqual(a.carry,1)
        self.assertEqual(a.view,'front-left');self.assertFalse(a.face_requested)

    def test_speech_request_can_be_withdrawn_without_cancelling_expression(self):
        a=Animator();a.set_view('front');a.play('turn');advance(a,.05)
        a.request_face_view('speech');a.request_face_view('speech',False);advance(a,1)
        self.assertEqual(a.view,'back');self.assertFalse(a.face_requested)
        a.play('spin');advance(a,.05);a.set_expression('happy')
        a.request_face_view('speech');a.request_face_view('speech',False);advance(a,2)
        self.assertEqual(a.view,'front-left')


if __name__=='__main__':unittest.main()
