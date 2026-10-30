#!/usr/bin/env python3
"""Reproduce component-selected source layers; no painting or landmark inference."""
import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QGuiApplication
from gpt_niang_linux.model.extraction import Atlas

ROOT=Path(__file__).resolve().parents[1]/'models/dragon'


def extract_all(destination):
    document=json.loads((ROOT/'source-selections.json').read_text())
    atlases={}; report={}
    for target,spec in document['layers'].items():
        if 'copy' in spec:
            source=destination/spec['copy']; out=destination/target
            out.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,out)
            report[target]={'copy':spec['copy']};continue
        source=ROOT/spec['source']
        if source not in atlases:atlases[source]=Atlas(source)
        image,meta=atlases[source].extract(spec['locator'],spec.get('include',[]))
        out=destination/target;out.parent.mkdir(parents=True,exist_ok=True)
        if not image.save(str(out)):raise OSError(f'Cannot save {out}')
        meta['source']=spec['source'];report[target]=meta
    (destination/'extraction-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();app=QGuiApplication([]);args.out.mkdir(parents=True,exist_ok=True)
    report=extract_all(args.out);print(f'Extracted {len(report)} layers to {args.out}')


if __name__=='__main__':main()
