#!/usr/bin/env python3
"""Render repeatable model contact sheets and sample animation; no account access."""
import argparse
import json
from pathlib import Path
import time

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

from gpt_niang_linux.model.assets import model_directory
from gpt_niang_linux.model.motion import Animator, EXPRESSIONS, MOTIONS
from gpt_niang_linux.model.render import DragonRenderer


def contact(renderer, entries, destination, expressions=False):
    cell, title_height, columns = 240, 28, 5
    rows = (len(entries)+columns-1)//columns
    output = QImage(cell*columns, (cell+title_height)*rows, QImage.Format.Format_ARGB32_Premultiplied)
    output.fill(QColor("#ddd8e8"))
    painter = QPainter(output)
    font = painter.font(); font.setPixelSize(14); painter.setFont(font)
    for index, (key, label) in enumerate(entries):
        animator = Animator()
        if not expressions and key in ("turn", "spin") and len(renderer.rigs) < 7:
            x, y = (index % columns)*cell, (index//columns)*(cell+title_height)
            painter.setPen(QColor("#81738e"))
            painter.drawText(QPointF(x+20, y+cell/2), label + " · 待绑定")
            continue
        if expressions:
            animator.set_expression(key)
            animator.clock = 1
        else:
            animator.play(key)
            # Exactly evaluate the middle of the action without a real-time timer.
            while animator.elapsed < MOTIONS[key][1]*(.99 if key in ("sit", "sleep", "stand") else .45) and animator.action:
                animator.advance(1/60)
        x, y = (index % columns)*cell, (index//columns)*(cell+title_height)
        painter.drawImage(QPointF(x, y), renderer.render(animator.pose(), cell))
        painter.setPen(QColor("#443857"))
        painter.drawText(QPointF(x+12, y+cell+20), label)
    painter.end(); output.save(str(destination))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("test-results/model"))
    parser.add_argument("--frames", action="store_true")
    args = parser.parse_args()
    app = QGuiApplication([])
    renderer = DragonRenderer(model_directory())
    args.out.mkdir(parents=True, exist_ok=True)
    contact(renderer, list(EXPRESSIONS.items()), args.out/"expressions.png", True)
    contact(renderer, [(k, v[0]) for k, v in MOTIONS.items()], args.out/"motions.png")
    animator = Animator(); animator.play("dance")
    duration, count = 0., 300
    for index in range(count):
        animator.advance(1/30)
        start = time.perf_counter()
        frame = renderer.render(animator.pose(), 320)
        frame.createAlphaMask(Qt.ImageConversionFlag.ThresholdAlphaDither)
        duration += time.perf_counter()-start
    metrics = {"frames": count, "size": 320, "meanRenderAndAlphaMs": round(duration/count*1000, 2),
               "backend": "QPainter CPU compositor; Quick upload excluded", "notLongRunAcceptance": True}
    (args.out/"metrics.json").write_text(json.dumps(metrics, indent=2)+"\n")
    if args.frames:
        animator = Animator(); animator.play("wave")
        frame_dir = args.out/"frames"; frame_dir.mkdir(exist_ok=True)
        for index in range(150):
            if index == 55: animator.play("tilt-left")
            if index == 110: animator.play("raise-both")
            animator.advance(1/30)
            renderer.render(animator.pose(), 512).save(str(frame_dir/f"{index:04}.png"))
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
