"""Surface regressions: endpoint identity, clipping, UV ownership and anatomy."""
from pathlib import Path
from dataclasses import replace
import math
import tempfile
import unittest

from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QColor,QImage,QPainter

from gpt_niang_linux.model.head import HeadFrame,ear_back_material
from gpt_niang_linux.model.motion import Animator
from gpt_niang_linux.model.render import DragonRenderer
from gpt_niang_linux.model.silhouette import draw_quad
from gpt_niang_linux.model.raster_mesh import draw_mesh
from test_model import synthetic_model


class HeadSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();root=Path(cls.tmp.name);synthetic_model(root)
        cls.renderer=DragonRenderer(root);cls.head=cls.renderer.layered_head

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_turn_direction_frames_keep_one_complete_native_silhouette(self):
        animator=Animator();animator.set_view('left');animator.clock=1.;pose=animator.pose()
        expected=self.renderer.render(pose,160)
        for angle in (80.,89.99,100.):
            actual=self.renderer.render(replace(pose,camera_angle=angle),160)
            self.assertEqual(bytes(actual.constBits()),bytes(expected.constBits()))
        for amount,view in ((.49,'left'),(.51,'back-left')):
            actual=self.renderer.render(replace(pose,blend_view='back-left',view_mix=amount),160)
            native=self.renderer.render(replace(pose,view=view),160)
            self.assertEqual(bytes(actual.constBits()),bytes(native.constBits()))

    def test_rear_and_profile_baked_necks_do_not_form_opaque_skin_blocks(self):
        for name in ('back-right','right','right247','right292'):
            frame=self.head.frame(name);self.assertTrue(frame.neck_regions)
            image=frame.image.convertToFormat(QImage.Format.Format_RGBA8888)
            pixels=bytes(image.constBits());count=0
            for index in range(image.width()*image.height()):
                world_y=frame.box[1]+index//image.width()/image.height()*frame.box[3]
                world_x=frame.box[0]+index%image.width()/image.width()*frame.box[2]
                if world_y<=468 or not any(x<=world_x<=x+w and y<=world_y<=y+h for x,y,w,h in frame.neck_regions):continue
                r,g,b,a=pixels[index*4:index*4+4]
                if a>128 and r>=175 and g>=110 and b>=110 and r>=b+2 and r>=g+1:count+=1
            self.assertLess(count,64,name)

    def test_all_head_surface_endpoints_use_the_complete_native_material(self):
        for name,angle in self.head.choices.items():
            a,b,_=self.renderer._neighbors(angle,self.head.choices)
            first,second=self.head.frame(a),self.head.frame(b)
            for phase in (.05,.2,.4,.65,.85,.95):
                y=first.palette.ys[0]+(first.palette.ys[-1]-first.palette.ys[0])*phase
                row,_,source_y,_=self.head.sample_rows(first,second,0,y)
                self.assertEqual(row,self.head.common_row(first,second,0,y),name)
                self.assertAlmostEqual(source_y,y,msg=name)
                self.assertTrue(all(left<=right for left,right in zip(row,row[1:])),name)

    def test_lower_curl_boundary_moves_continuously_between_materials(self):
        for angle in self.head.choices.values():
            a,b,_=self.renderer._neighbors(angle,self.head.choices);a,b=self.head.frame(a),self.head.frame(b)
            for amount in (.49999,.5,.50001):
                bottom=a.palette.ys[-1]+(b.palette.ys[-1]-a.palette.ys[-1])*amount
                _,_,ay,by=self.head.sample_rows(a,b,amount,bottom)
                self.assertAlmostEqual(ay,a.palette.ys[-1]);self.assertAlmostEqual(by,b.palette.ys[-1])

    def test_covered_face_rows_do_not_jump_to_the_outer_head_edge(self):
        for angle,y in ((78.75,270),(123.75,287),(235,279)):
            a,b,t=self.renderer._neighbors(angle,self.head.choices);a,b=self.head.frame(a),self.head.frame(b)
            first=self.head.common_row(a,b,t,y);second=self.head.common_row(a,b,t,y+1)
            self.assertLess(max(abs(x-z) for x,z in zip(first,second)),30.,angle)

    def test_canonical_features_keep_the_source_texture_mirror(self):
        for name in ('right','right247','right292'):
            frame=self.head.frame(name)
            self.assertTrue(frame.face['flip'])
            for key,spec in frame.feature_specs.items():
                original=frame.face['features'][key]
                self.assertEqual(spec['flipX'],bool(original.get('flipX'))^True)

    def test_expression_decorations_remain_on_visible_anatomical_cheeks(self):
        front=self.head.frame('front');layout=self.head._layout(front,front,0)
        self.assertTrue(all(rect[0]>0 and rect[2]>0 for rect in layout['blush']))
        self.assertTrue(all(point[0]>0 and point[1]>0 for point in layout['tears']))
        profile=self.head.frame('left');layout=self.head._layout(profile,profile,0)
        self.assertEqual(layout['eyeOpacity'],[0.,1.]);self.assertEqual(layout['winkEye'],1)

    def test_back_ear_material_has_the_exact_same_alpha_and_root_coordinates(self):
        for name in ('earLeft','earRight'):
            front=self.head.parts[name];back=self.head.parts[name+'Back']
            self.assertEqual(front[1:],back[1:]);self.assertEqual(front[0].size(),back[0].size())
            a=front[0].convertToFormat(QImage.Format.Format_RGBA8888)
            b=back[0].convertToFormat(QImage.Format.Format_RGBA8888)
            self.assertEqual(bytes(a.constBits())[3::4],bytes(b.constBits())[3::4])
            rgba=bytes(b.constBits())
            self.assertFalse(any(rgba[i+3]>128 and max(rgba[i:i+3])<32 for i in range(0,len(rgba),4)))

    def test_tail_inner_bend_and_shaft_keep_adjacent_source_pixels_adjacent(self):
        a=Animator();a.set_view('back');a.play('land');a.advance(.325);pose=a.pose()
        rest,posed=self.renderer._tail_geometry(pose);mapping=self.renderer._tail_mapping(pose,rest,posed)
        self.assertEqual(self.renderer._tail_skin('back').height,256)
        x,y,w,h=self.renderer.puppet['tailViews']['back']['box']
        for pair in (((168,636),(168,637)),((316,1166),(317,1166))):
            points=[(x+xx/610*w,y+yy/1391*h) for xx,yy in pair]
            self.assertLess(math.dist(*(mapping(p) for p in points)),math.dist(*points)*1.5)


class RasterSafetyTests(unittest.TestCase):
    def test_neck_cleanup_preserves_small_warm_hair_pixels_even_inside_the_roi(self):
        frame=HeadFrame.__new__(HeadFrame)
        frame.image=QImage(210,210,QImage.Format.Format_ARGB32_Premultiplied);frame.image.fill(QColor('white'))
        painter=QPainter(frame.image);painter.fillRect(80,150,30,30,QColor('#f4d6c5'));painter.end()
        frame.image.setPixelColor(90,145,QColor('#f4d6c5'))
        frame.box=[320.,300.,210.,210.];frame.face=None;frame.neck_regions=[[395,440,40,50]]
        frame._skin_rows()
        self.assertEqual(frame.image.pixelColor(95,165).alpha(),0)
        self.assertEqual(frame.image.pixelColor(90,145).alpha(),255)
        self.assertEqual(frame.image.pixelColor(160,170).alpha(),255)

    def test_airborne_replays_and_new_jumps_preserve_the_current_flight(self):
        for action in ('jump','hop','toss','flap'):
            a=Animator();a.set_view('front');a.play('jump')
            for _ in range(63):a.advance(.01)
            before=a.pose();a.play(action);after=a.pose()
            self.assertTrue(after.airborne,action);self.assertAlmostEqual(after.root_y,before.root_y)
            self.assertAlmostEqual(after.vertical_velocity,before.vertical_velocity)
            self.assertIsNotNone(a.fall);self.assertEqual(a.after_land,action)

    def test_throw_releases_from_the_current_grab_height(self):
        a=Animator();a.set_view('front');a.play('carried')
        for _ in range(50):a.advance(.01)
        height=a.pose().root_y;a.play('toss')
        self.assertAlmostEqual(a.pose().root_y,height);self.assertTrue(a.pose().airborne)
        self.assertLess(a.pose().vertical_velocity,-400)
        for _ in range(20):self.assertLess(a.advance(.01).root_y,height)
        self.assertFalse(a.after_land)
    def test_mesh_composite_keeps_its_world_position_after_local_source_sampling(self):
        source=QImage(16,16,QImage.Format.Format_ARGB32_Premultiplied);source.fill(QColor('white'))
        output=QImage(600,600,QImage.Format.Format_ARGB32_Premultiplied);output.fill(Qt.GlobalColor.transparent)
        painter=QPainter(output);draw_mesh(painter,source,[300,400,48,100],lambda p:(p[0]+20,p[1]+10),columns=3,rows=8);painter.end()
        rgba=output.convertToFormat(QImage.Format.Format_RGBA8888);alpha=bytes(rgba.constBits())[3::4]
        points=[(i%600,i//600) for i,a in enumerate(alpha) if a>128]
        self.assertLess(abs(min(x for x,y in points)-320),2);self.assertLess(abs(min(y for x,y in points)-410),2)
        self.assertLess(abs(max(x for x,y in points)-367),2);self.assertLess(abs(max(y for x,y in points)-509),2)

    def test_closing_quad_cannot_paint_a_wedge_outside_its_target(self):
        source=QImage(16,16,QImage.Format.Format_ARGB32_Premultiplied);source.fill(QColor('white'))
        output=QImage(128,128,QImage.Format.Format_ARGB32_Premultiplied);output.fill(Qt.GlobalColor.transparent)
        painter=QPainter(output)
        draw_quad(painter,source,[(0,0),(1e-9,0),(16,16),(0,16)],[(40,40),(40.0001,40),(60,80),(40,80)])
        painter.end();rgba=output.convertToFormat(QImage.Format.Format_RGBA8888);alpha=bytes(rgba.constBits())[3::4]
        self.assertGreater(max(alpha),0)
        self.assertFalse(any(a for i,a in enumerate(alpha) if i%128<38 or i%128>62 or i//128<38 or i//128>82))

    def test_late_run_cancel_settles_limbs_without_a_one_millisecond_reset(self):
        a=Animator();a.set_view('left');a.play('run')
        for _ in range(1000):
            if a.elapsed>=7.499/2.1:break
            a.advance(min(.01,7.499/2.1-a.elapsed))
        previous=a.pose();a.cancel()
        for _ in range(5):
            current=a.advance(.001)
            for node in previous.legs:
                self.assertLess(math.dist((previous.legs[node]['x'],previous.legs[node]['y']),(current.legs[node]['x'],current.legs[node]['y'])),3.)
            previous=current


if __name__=='__main__':unittest.main()
