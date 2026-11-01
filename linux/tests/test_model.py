"""Lifecycle, pose isolation, import security and animated hit regions."""
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QBitmap, QGuiApplication, QImage, QRegion

from gpt_niang_linux.model.assets import import_model, validate_model
from gpt_niang_linux.model.item import DragonItem
from gpt_niang_linux.model.motion import Animator, EXPRESSIONS, MOTIONS, VIEWS
from gpt_niang_linux.model.render import DragonRenderer

app = QGuiApplication.instance() or QGuiApplication([])


def advance(animator, seconds):
    for _ in range(round(seconds*100)):
        animator.advance(.01)


def synthetic_model(root):
    # These solid pixels are geometry fixtures, never substitute character artwork.
    names = 'hair-back wing-far wing-near tail leg-far leg-near skirt-far skirt-near arm-far neck torso sit apron arm-near ear-far ear-near face nose mouth eye-far-white eye-near-white eye-far-iris eye-near-iris horns hair-front ahoge eye-far-lash eye-near-lash brow-far brow-near'.split()
    parents = 'hairBack wingFar wingNear tail legFar legNear skirtFar skirtNear armFar upper upper seat apron armNear head head head head features features features features features head hairFront ahoge features features features features'.split()
    parts = []; (root/'tex').mkdir()
    for index, (name, parent) in enumerate(zip(names, parents)):
        box = {'arm-near': [457,473,114,202], 'hair-back': [231,127,509,615], 'sit': [92,570,804,345]}.get(name, [300,400,55,55])
        # Separate the facial fixtures: coincident opaque brows would cover
        # both eyes and mouth and make the live-preview check meaningless.
        box={'eye-far-white':[300,340,50,48],'eye-near-white':[410,340,50,48],
             'eye-far-iris':[310,344,30,40],'eye-near-iris':[420,344,30,40],
             'eye-far-lash':[298,335,55,16],'eye-near-lash':[408,335,55,16],
             'brow-far':[302,325,45,8],'brow-near':[412,325,45,8],
             'mouth':[380,420,14,10],'nose':[383,400,8,8]}.get(name,box)
        part = dict(id=name, src=f'tex/{name}.png', parent=parent, box=box, z=index)
        im = QImage(box[2], box[3], QImage.Format.Format_ARGB32)
        im.fill(QColor.fromHsv(index*11 % 360, 160, 220)); im.save(str(root/part['src']))
        parts.append(part)
    pivots={name:[425,574] for name in set(parents) if name != 'features'}
    pivots.update(upper=[425,574],head=[425,460],armNear=[479,491])
    model = dict(source={'canvas': [1024,1024]}, parts=parts,pivots=pivots)
    (root/'model.json').write_text(json.dumps(model))
    return model


class AnimationTests(unittest.TestCase):
    def test_catalog_matches_baseline(self):
        data = json.loads((Path(__file__).parents[1]/'docs/coopanion-dragon-baseline.json').read_text())
        self.assertEqual(set(EXPRESSIONS), {x['id'] for x in data['expressions']})
        self.assertTrue({x['id'] for x in data['motions']} <= MOTIONS.keys())
        self.assertEqual(len(VIEWS), 8)

    def test_seated_pose_persists_and_stand_restores(self):
        a = Animator(); a.play('sit'); advance(a, 2)
        self.assertEqual(a.seat, 1); self.assertFalse(a.action)
        advance(a, 20); self.assertEqual(a.seat, 1)
        a.play('sleep'); advance(a, 2); self.assertTrue(a.pose().eye_closed)
        a.play('stand'); advance(a, 2)
        self.assertEqual(a.seat, 0); self.assertFalse(a.pose().eye_closed)
        for _ in range(30):
            a.play('sit'); advance(a, 1); a.play('stand'); advance(a, 2)
        self.assertEqual(a.pose().transforms['upper']['y'], 0)
        self.assertAlmostEqual(a.pose().root_angle, 0)

    def test_reorient_before_gesture_and_cancel_discards_queue(self):
        a = Animator(); a.set_view('back'); a.play('wave')
        self.assertEqual(a.action, 'turn'); self.assertEqual(a.pending, 'wave')
        advance(a, .6); self.assertEqual(a.view, 'front'); self.assertEqual(a.action, 'wave')
        a.set_view('back'); a.play('wave'); a.cancel(); advance(a, 2)
        self.assertFalse(a.action); self.assertFalse(a.pending)

    def test_tilt_is_head_only_and_hands_are_distinct(self):
        poses = {}
        for action in ('tilt-left','tilt-right','raise-left','raise-right','raise-both','wave'):
            a = Animator(); a.set_view('front'); a.play(action); advance(a, .6); poses[action] = a.pose()
        self.assertLess(poses['tilt-left'].transforms['head']['a'], -5)
        self.assertGreater(poses['tilt-right'].transforms['head']['a'], 5)
        self.assertEqual(poses['tilt-left'].root_angle, 0)
        self.assertLess(poses['raise-left'].transforms['armNear']['a'], -90)
        self.assertGreater(poses['raise-right'].transforms['armFar']['a'], 90)
        self.assertNotEqual(poses['wave'].transforms['armNear']['a'], poses['raise-left'].transforms['armNear']['a'])

    def test_replacement_discards_pending_gesture_and_carry_holds_until_release(self):
        a = Animator(); a.set_view('back'); a.play('wave'); a.play('stand'); advance(a, 2)
        self.assertFalse(a.action or a.pending)
        a.play('carried'); advance(a, 8); self.assertEqual(a.action, 'carried')
        a.play('land'); advance(a, 1); self.assertFalse(a.action)

    def test_turn_visits_intermediate_views_and_spin_returns_to_start(self):
        a=Animator(); a.set_view('front-left'); a.play('turn'); seen=set()
        for _ in range(round(MOTIONS['turn'][1]*100)+5): a.advance(.01); seen.add(a.view)
        self.assertGreaterEqual(len(seen),4); self.assertEqual(a.view,'back-right')
        start=a.view; a.play('spin'); seen=set()
        for _ in range(round(MOTIONS['spin'][1]*100)+5): a.advance(.01); seen.add(a.view)
        self.assertEqual(seen,set(VIEWS)); self.assertEqual(a.view,start)
        a.set_view('front'); a.play('sit'); self.assertEqual(a.pending,'sit')
        advance(a,1.4); self.assertEqual(a.view,'front-left'); self.assertEqual(a.seat,1)

    def test_pause_speed_and_reset(self):
        a = Animator(); a.play('sleep'); advance(a, 1); a.speech = a.listening = True
        a.paused = True; before = a.clock; advance(a, 3); self.assertEqual(a.clock, before)
        a.cancel(); self.assertEqual(a.seat, 1); self.assertEqual(a.action,'stand')
        self.assertFalse(a.speech or a.listening or a.sleeping)
        a.paused = False; a.speed = .5; advance(a, 1); self.assertAlmostEqual(a.clock-before, .5)
        advance(a,2);self.assertEqual(a.seat,0)


class ResourceTests(unittest.TestCase):
    def test_pointing_ray_tracks_the_authored_bubble_target_after_rebinding(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp);synthetic_model(source);renderer=DragonRenderer(source)
            data,images=renderer.rigs['front'];arm=next(p for p in data['parts'] if p['id']=='arm-near')
            spec=arm['articulation'];hand=spec['segments']['point']
            for seconds in (.1,.3,.6,1.8):
                a=Animator();a.set_view('front');a.play('point');advance(a,seconds)
                chain=renderer._arm_geometry(arm,images,a.pose(),data['pivots'])
                v=chain['point'];px,py=chain['hand']['root'];x,y,w,h=v['box']
                tx,ty=x+hand['endUV'][0]*w-px,y+hand['endUV'][1]*h-py
                im=images['arm-near#point'];dx,dy=hand['indexRay'][0]*w/im.width(),hand['indexRay'][1]*h/im.height()
                c,s=math.cos(math.radians(v['rotation'])),math.sin(math.radians(v['rotation']))
                tip=(px+c*tx-s*ty,py+s*tx+c*ty);ray=(c*dx-s*dy,s*dx+c*dy)
                target=(spec['pointTarget'][0]-tip[0],spec['pointTarget'][1]-tip[1])
                self.assertAlmostEqual((ray[0]*target[1]-ray[1]*target[0])/math.hypot(*ray),0,delta=.01)
                self.assertGreater(ray[0]*target[0]+ray[1]*target[1],0)

    def test_look_back_preserves_the_rear_body_feet(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp);synthetic_model(source);renderer=DragonRenderer(source)
            for view in ('back-left','back-right'):
                a=Animator();a.set_view(view);a.play('look-back');advance(a,1);pose=a.pose()
                looking=renderer.render(pose,320);pose.look_back=0;rear=renderer.render(pose,320)
                self.assertNotEqual(looking,rear)
                self.assertEqual(looking.copy(0,280,320,40),rear.copy(0,280,320,40))

    def test_replacing_a_gesture_keeps_the_visible_elbow_and_wrist(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp);synthetic_model(source);renderer=DragonRenderer(source)
            data,images=renderer.rigs['front'];arm=next(p for p in data['parts'] if p['id']=='arm-near')
            for replacement in ('stand','raise-right','point','carried',None):
                a=Animator();a.set_view('front');a.play('raise-both');advance(a,.23)
                before=renderer._arm_geometry(arm,images,a.pose(),data['pivots'])
                if replacement:a.play(replacement)
                else:a.cancel()
                after=renderer._arm_geometry(arm,images,a.pose(),data['pivots'])
                for node in ('upper','forearm','hand'):
                    self.assertLess(math.dist(before[node]['root'],after[node]['root']),1,replacement)
                    self.assertLess(math.dist(before[node]['end'],after[node]['end']),1,replacement)

    def test_unknown_archive_and_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); archive = root/'model.zip'
            with zipfile.ZipFile(archive, 'w') as z: z.writestr('../../escape', 'bad')
            with self.assertRaises(ValueError): import_model(archive, root/'destination')
            model = synthetic_model(root); model['parts'][0]['src'] = '../../escape.png'
            with self.assertRaises(ValueError): validate_model(model)
            self.assertFalse((root/'destination').exists())

    def test_import_is_data_only_and_preserves_unrelated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root/'source'; source.mkdir(); synthetic_model(source)
            (source/'figure.json').write_text('{}'); (source/'README.md').write_text('source notice')
            (source/'thumb.png').write_bytes((source/'tex/face.png').read_bytes())
            archive = root/'model.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                for path in source.rglob('*'):
                    if path.is_file(): z.write(path, 'gpt-dragon/'+str(path.relative_to(source)))
                z.writestr('gpt-dragon/figure.js', 'throw Error("must never execute")')
                z.writestr('../../escape', 'must never extract')
            with patch('gpt_niang_linux.model.assets.SOURCE_SHA256', hashlib.sha256(archive.read_bytes()).hexdigest()):
                out = import_model(archive, root/'out')
                self.assertTrue((out/'README.md').exists()); self.assertFalse((out/'figure.js').exists())
                self.assertFalse((root/'escape').exists()); self.assertEqual(import_model(archive, out), out)
                (out/'README.md').write_text('modified')
                import_model(archive, out)
                self.assertEqual((out/'README.md').read_text(), 'source notice')
                backups = list(root.glob('out.backup-*')); self.assertEqual(len(backups), 1)
                self.assertEqual((backups[0]/'README.md').read_text(), 'modified')
                unrelated = root/'unrelated'; unrelated.mkdir(); (unrelated/'keep').write_text('keep')
                with self.assertRaises(ValueError): import_model(archive, unrelated)
                self.assertEqual((unrelated/'keep').read_text(), 'keep')

    def test_composite_changes_hit_region_and_leaves_empty_space_transparent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); synthetic_model(root)
            with patch("gpt_niang_linux.model.render.LINUX_ROOT", root):
                renderer = DragonRenderer(root)
            a = Animator(); neutral = renderer.render(a.pose(), 320)
            a.play('raise-left'); advance(a, .6); raised = renderer.render(a.pose(), 320)
            self.assertFalse(neutral == raised)
            flags = Qt.ImageConversionFlag.ThresholdAlphaDither
            region1 = QRegion(QBitmap.fromImage(neutral.createAlphaMask(flags)))
            region2 = QRegion(QBitmap.fromImage(raised.createAlphaMask(flags)))
            self.assertFalse(region1 == region2); self.assertFalse(region2.contains(QPoint(0,0)))
            self.assertFalse(region2.isEmpty())

    def test_optional_broken_view_does_not_remove_the_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root/'source'; source.mkdir(); synthetic_model(source)
            extra = root/'models/dragon'; extra.mkdir(parents=True)
            (extra/'views.json').write_text(json.dumps({'views': {'back': {'rig': 'missing.json'}}}))
            with patch('gpt_niang_linux.model.render.LINUX_ROOT', root):
                renderer = DragonRenderer(source)
            self.assertEqual(renderer.view_errors, ['back']); self.assertFalse(renderer.rigs)
            self.assertFalse(renderer.render(Animator().pose(), 320).isNull())

    def test_checked_in_views_and_hashes_render_without_the_private_source_pack(self):
        workspace=Path(__file__).parents[1]/'models/dragon'
        manifest=json.loads((workspace/'asset-hashes.json').read_text())
        for name,digest in manifest['sha256'].items():
            self.assertEqual(hashlib.sha256((workspace/name).read_bytes()).hexdigest(),digest,name)
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp); synthetic_model(source); renderer=DragonRenderer(source)
            self.assertEqual(len(renderer.rigs),7); self.assertFalse(renderer.view_errors)
            hashes=set(); a=Animator()
            for view in VIEWS:
                a.set_view(view); frame=renderer.render(a.pose(),320)
                self.assertFalse(frame.isNull()); hashes.add(hashlib.sha256(frame.constBits()).hexdigest())
            self.assertEqual(len(hashes),8)

    def test_paused_preview_updates_and_closing_it_preserves_controller_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp); synthetic_model(source)
            with patch('gpt_niang_linux.model.item.model_directory',return_value=source):
                controller=DragonItem(); preview=DragonItem()
            controller.timer.stop(); preview.timer.stop()
            for item in (controller,preview): item.setWidth(320);item.setHeight(320)
            preview.follow=controller; controller.setPaused(True)
            before=hashlib.sha256(preview.frame.constBits()).hexdigest()
            controller.setExpression('happy')
            self.assertNotEqual(before,hashlib.sha256(preview.frame.constBits()).hexdigest())
            preview.active=False
            self.assertEqual(controller.expression,'happy'); self.assertTrue(controller.paused)

    def test_unbound_views_and_actions_not_advertised_as_ready(self):
        with tempfile.TemporaryDirectory() as tmp, patch('gpt_niang_linux.model.item.model_directory', return_value=Path(tmp)):
            item = DragonItem(); item.timer.stop()
            self.assertFalse(item.available)
            self.assertFalse(any(m['ready'] for m in item.motions if m['id'] in ('turn','spin')))
            item.play('turn'); self.assertFalse(item.motion)


if __name__ == '__main__': unittest.main()
