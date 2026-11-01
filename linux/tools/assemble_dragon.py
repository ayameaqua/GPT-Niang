#!/usr/bin/env python3
"""Reproduce selected source islands and explicit per-view bindings.

Selection locators choose a complete component, never clip to a shared atlas
cell. Geometry and joints live in rig-layouts.json and are reviewed together.
"""
import json
import hashlib
import argparse
from pathlib import Path
from PySide6.QtGui import QGuiApplication
from extract_dragon import extract_all

ROOT=Path(__file__).resolve().parents[1]/'models/dragon'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--hashes-only',action='store_true');args=parser.parse_args()
    app=QGuiApplication([])
    if not args.hashes_only:
        extract_all(ROOT)
        layouts=json.loads((ROOT/'rig-layouts.json').read_text())
        manifest={}
        for view,rig in layouts['views'].items():
            (ROOT/view/'rig.json').write_text(json.dumps(rig,ensure_ascii=False,indent=2)+'\n')
            manifest[view]={'rig':f'{view}/rig.json','status':rig['status']}
        (ROOT/'views.json').write_text(json.dumps({'schemaVersion':1,'views':manifest},indent=2)+'\n')
        print(f'Assembled {len(manifest)} explicit view rigs')
    paths=sorted([*ROOT.rglob('*.png'),*ROOT.glob('*/rig.json'),ROOT/'views.json',ROOT/'rig-layouts.json',ROOT/'source-selections.json',*ROOT.glob('puppet.json'),*ROOT.glob('head.json')])
    hashes={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    (ROOT/'asset-hashes.json').write_text(json.dumps({'schemaVersion':1,'generator':'built-in image_gen.imagegen; component extraction and explicit Qt bindings','sha256':hashes},indent=2)+'\n')


if __name__=='__main__':main()
