#!/usr/bin/env python3

import bimpy
from PIL import Image
from argparse import ArgumentParser
from time import (time, sleep)
import os

__version__ = "0.1"

DEF_WIDTH = 16
DEF_HEIGHT = 16
DEF_SCALE = 14
DEF_MTIME = 5


def with_retry(fn):
    def wrap():
        retry = 0
        while True:
            try:
                result = fn()
            except IOError:
                retry += 1
                sleep(1)
                if retry == 3:
                    raise
            else:
                return result
    return wrap


def main():

    parser = ArgumentParser(description="Preview animations")

    parser.add_argument("--version", action="version",
                        version="%(prog)s " + __version__)
    parser.add_argument("--width", dest="width", type=int, default=DEF_WIDTH,
                        help="frame width (default: %s)" % DEF_WIDTH)
    parser.add_argument("--height", dest="height", type=int, default=DEF_HEIGHT,
                        help="frame height (default: %s)" % DEF_HEIGHT)
    parser.add_argument("--scale", dest="scale", type=int, default=DEF_SCALE,
                        help="scale preview (default: %s)" % DEF_SCALE)
    parser.add_argument("--double-w", dest="dw", action="store_true",
                        help="double width for 2:1")
    parser.add_argument("--mtime", dest="mtime", type=int, default=DEF_MTIME,
                        help="seconds between checks for changes (default: %s)" % DEF_MTIME)

    parser.add_argument("image", help="image to preview")

    args = parser.parse_args()

    def load_image(filename):
        @with_retry
        def load():
            return Image.open(filename).convert("RGB")

        try:
            image = load()
        except IOError:
            parser.error("failed to open the image")

        (w, h) = image.size

        if w % args.width or h % args.height:
            parser.error("%s size is not multiple of tile size (%s, %s)" %
                         (filename, args.width, args.height))

        frames = []
        for y in range(0, h, args.height):
            for x in range(0, w, args.width):
                frames.append((x, y, x + args.width, y + args.height))

        return image, frames

    image, frames = load_image(args.image)
    frame_list = list(range(len(frames)))

    def scale_image(scale, frameno):
        scale_w = scale if not args.dw else scale * 2
        current = image.resize(
            (args.width * scale_w, args.height * scale), box=frames[frame_list[frameno]],
            resample=0)
        return bimpy.Image(current)

    ctx = bimpy.Context()

    ctx.init(320, 420, "Preview animation")
    orig = bimpy.Image(image)
    scale = bimpy.Int(args.scale)
    fps = bimpy.Int(args.scale)
    frame_list_str = bimpy.String(','.join(map(str, frame_list)))
    im = scale_image(scale.value, 0)

    cur_frame = 0
    paused = False
    start_time = time()
    check_mtime = time()
    last_mtime = os.stat(args.image).st_mtime
    while(not ctx.should_close()):

        if time() - check_mtime > args.mtime:
            if os.stat(args.image).st_mtime != last_mtime:
                last_mtime = os.stat(args.image).st_mtime
                image, frames = load_image(args.image)
                cur_frame = 0
                start_time = time()
                if any([f >= len(frames) for f in frame_list]):
                    frame_list = list(range(len(frames)))
                    frame_list_str = bimpy.String(
                        ','.join(map(str, frame_list)))

        ctx.new_frame()
        bimpy.set_next_window_pos(bimpy.Vec2(10, 10), bimpy.Condition.Once)
        bimpy.set_next_window_size(bimpy.Vec2(300, 400), bimpy.Condition.Once)
        bimpy.begin("Image: %s" % args.image)

        if not paused:
            if time() - start_time >= 1. / fps.value:
                start_time = time()
                cur_frame += 1
                if cur_frame == len(frame_list):
                    cur_frame = 0
                im = scale_image(scale.value, cur_frame)

        bimpy.image(orig)
        bimpy.image(im)
        bimpy.text("Frame: %02d" % frame_list[cur_frame])

        if bimpy.slider_int("Scale", scale, 1, 20):
            im = scale_image(scale.value, cur_frame)
        if bimpy.slider_int("FPS", fps, 1, 30):
            start_time = time()
            cur_frame = 0
        if bimpy.input_text("Frames", frame_list_str, 64, bimpy.InputTextFlags.EnterReturnsTrue):
            try:
                new_frame_list = [int(i.strip())
                                  for i in frame_list_str.value.split(",")]
                frame_list = new_frame_list
                start_time = time()
                cur_frame = 0
            except Exception as ex:
                print("Error parsing frame list: %s" % ex)

        if bimpy.button("Play" if paused else "Pause"):
            paused = not paused

        bimpy.end()
        ctx.render()


if __name__ == "__main__":
    main()
