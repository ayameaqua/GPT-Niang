"""Regressions for articulated motion and interruption, rather than sprite shifts."""
from dataclasses import replace
import math
from pathlib import Path
import tempfile
import unittest

from gpt_niang_linux.model.kinematics import coccyx_point,head_point,skin_point,solve_leg
from gpt_niang_linux.model.motion import Animator,MOTIONS
from gpt_niang_linux.model.render import DragonRenderer
from test_model import synthetic_model


def advance(animator,seconds,step=.01):
    while seconds>1e-10:
        dt=min(step,seconds);animator.advance(dt);seconds-=dt


def physical(pose):
    def flatten(value):
        if isinstance(value,dict):
            return {key:flatten(val) for key,val in value.items()}
        if isinstance(value,(tuple,list)):return tuple(flatten(val) for val in value)
        return round(float(value),7)
    return {name:flatten(getattr(pose,name)) for name in
            ('transforms','root_x','root_y','root_angle','root_anchor','pelvis','legs',
             'seat','head_pitch','head_yaw','hands','arm_base','blink','turn_tail')}


class SkeletalTests(unittest.TestCase):
    def test_knee_preserves_lengths_in_depth_instead_of_splaying_frontally(self):
        hip=(425.,650.);ankle=(425.,900.)
        front,end=solve_leg(hip,ankle,150,150,view_angle=0)
        side,_=solve_leg(hip,ankle,150,150,view_angle=90)
        self.assertAlmostEqual(math.dist((*hip,0),front),150)
        self.assertAlmostEqual(math.dist(front,end),150)
        self.assertAlmostEqual(front[0],hip[0]);self.assertGreater(front[2],50)
        self.assertLess(side[0],hip[0]-50)

    def test_boot_is_a_rigid_end_bone(self):
        rest=[(0,0),(0,100),(0,200),(40,215)]
        posed=[(10,50),(-30,110),(20,200),(20+40*.8-15*.6,200+40*.6+15*.8)]
        a=skin_point((9,207),rest,posed,(0,0,1))
        b=skin_point((31,219),rest,posed,(0,0,1))
        self.assertAlmostEqual(math.dist(a,b),math.dist((9,207),(31,219)))

    def test_head_pitch_preserves_face_proportions_and_has_no_old_seam(self):
        box=[190,65,470,470];neck=(425,460)
        eye=(370,397);mouth=(425,438)
        a=head_point(eye,neck,box,12,0,'front');b=head_point(mouth,neck,box,12,0,'front')
        self.assertGreater(math.dist(a,b),math.dist(eye,mouth)*.85)
        boundary=box[1]+box[3]*.29
        a=head_point((425,boundary-.0001),neck,box,12,0,'front')
        b=head_point((425,boundary+.0001),neck,box,12,0,'front')
        self.assertLess(math.dist(a,b),.001)
        self.assertNotAlmostEqual(a[1]-(boundary-.0001),head_point(eye,neck,box,12,0,'front')[1]-eye[1])

    def test_profile_yaw_moves_the_visible_face(self):
        point=(375,380);neck=(418,465);box=[238,65,473,456]
        self.assertGreater(math.dist(head_point(point,neck,box,0,10,'left'),point),.1)

    def test_coccyx_rotates_with_seated_pelvis(self):
        standing=coccyx_point(90,0);sitting=coccyx_point(90,1)
        self.assertEqual(standing,(475,683))
        self.assertAlmostEqual(sitting[0],506);self.assertAlmostEqual(sitting[1],652)


class PerformanceTests(unittest.TestCase):
    def test_nod_uses_pitch_with_stationary_attachment(self):
        a=Animator();a.set_view('front');a.play('nod');advance(a,.6)
        pose=a.pose();self.assertGreater(pose.head_pitch,10)
        self.assertEqual(pose.transforms['head']['y'],0)
        self.assertEqual(pose.transforms['head']['sy'],1)

    def test_jump_crouches_on_supported_feet_then_tucks_in_air(self):
        a=Animator();a.set_view('front');a.play('jump');advance(a,.2)
        crouch=a.pose();self.assertGreater(crouch.pelvis[1],35)
        self.assertEqual(crouch.root_y,0);self.assertEqual(crouch.contacts,(True,True))
        advance(a,.4);flight=a.pose();self.assertTrue(flight.airborne)
        self.assertLess(flight.root_y,-100)
        self.assertTrue(all(state['y']<-40 for state in flight.legs.values()))
        advance(a,.48);self.assertFalse(a.pose().airborne)
        self.assertGreater(a.pose().pelvis[1],25)

    def test_stance_foot_cancels_body_sway(self):
        for action in ('walk','run'):
            a=Animator();a.set_view('left');a.play(action)
            for _ in range(350):
                p=a.advance(.01)
                for contact,node in zip(p.contacts,('legFar','legNear')):
                    if contact:self.assertAlmostEqual(p.root_x+p.legs[node]['x'],0,places=6)

    def test_cancel_retains_the_entire_physical_pose_at_same_clock(self):
        for action,(_,duration) in MOTIONS.items():
            a=Animator();a.set_view('front');a.play(action)
            for _ in range(200):
                if not a.pending:break
                a.advance(.01)
            advance(a,duration*.43)
            before=physical(a.pose());a.cancel()
            self.assertEqual(before,physical(a.pose()),action)

    def test_run_cancel_continues_short_arc_without_becoming_a_large_jump(self):
        for phase in (.401,.41,.45,.49,.499):
            a=Animator();a.set_view('left');a.play('run');advance(a,(7+phase)/2.1)
            before=a.pose();a.cancel();self.assertAlmostEqual(a.pose().root_y,before.root_y)
            values=[a.pose().root_y]
            for _ in range(800):values.append(a.advance(.001).root_y)
            self.assertGreaterEqual(min(values),-12.0001,phase)
            self.assertTrue(all(y<=0 for y in values))
            self.assertFalse(a.action);self.assertEqual(a.pose().root_y,0)
            self.assertLess(max(abs(x-y) for x,y in zip(values,values[1:])),1)

    def test_repeated_run_fall_cancel_keeps_its_flight_owner(self):
        a=Animator();a.set_view('left');a.play('run');advance(a,7.41/2.1)
        a.cancel();advance(a,.005,step=.001);a.cancel()
        values=[a.advance(.001).root_y for _ in range(800)]
        self.assertGreaterEqual(min(values),-12.0001);self.assertFalse(a.action)

    def test_rear_toss_expression_waits_for_landing_without_replaying(self):
        a=Animator();a.set_view('back');a.play('toss');advance(a,.735)
        before=a.pose();a.set_expression('happy')
        self.assertEqual(a.action,'toss');self.assertTrue(a.pose().airborne)
        self.assertEqual(a.pose().root_y,before.root_y)
        seen_toss_finished=False
        for _ in range(300):
            p=a.advance(.01)
            if a.action!='toss':seen_toss_finished=True
            if seen_toss_finished:self.assertNotEqual(a.action,'toss')
            if a.action=='turn':self.assertFalse(p.airborne)
        self.assertFalse(a.face_requested)

    def test_interrupted_expression_and_accent_are_pixel_continuous(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);synthetic_model(root);renderer=DragonRenderer(root)
            for expression in ('happy','angry','confused','thinking'):
                a=Animator();a.set_view('front');a.set_expression(expression);advance(a,.08)
                before=renderer.render(a.pose(),320);a.cancel();after=renderer.render(a.pose(),320)
                self.assertEqual(bytes(before.constBits()),bytes(after.constBits()),expression)

    def test_sleep_cancel_stands_then_opens_lids(self):
        a=Animator();a.play('sleep');advance(a,2);a.cancel()
        self.assertEqual(a.action,'stand');self.assertGreater(a.pose().blink,.99)
        advance(a,.1);self.assertGreater(a.pose().blink,.3)
        advance(a,1.3);self.assertEqual(a.seat,0);self.assertFalse(a.pose().eye_closed)

    def test_turn_retracts_tail_once_across_all_direction_keyframes(self):
        a=Animator();a.play('spin');values=[]
        for _ in range(160):values.append(a.advance(.01).turn_tail)
        self.assertEqual(max(values),1)
        self.assertTrue(all(v>.999 for v in values[26:135]))
        self.assertLess(values[-1],.001)


if __name__=='__main__':unittest.main()
