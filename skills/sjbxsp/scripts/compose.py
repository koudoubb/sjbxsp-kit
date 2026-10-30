#!/usr/bin/env python3
"""逐页帧序列 -> 每页视频 -> 拼接 -> 逐帧 alpha 合成字幕 -> 混音 -> final.mp4

用法：
  python compose.py --base <项目目录> [--anim anim] [--audio narration.mp3]
                    [--fps 25] [--anim-dur 4.0] [--band-y 1500] [--band-h 420]
                    [--out build/final.mp4] [--crf 18]

为什么不用 ffmpeg 的 subtitles/overlay：
  * 本机 ffmpeg 构建**没有 libass**，subtitles / ass 滤镜不可用；
  * 用 concat 拼字幕 filmstrip 会每段累积约 1 帧，后段越来越晚（实测 3 分钟漂 2.5s）。
  所以：解码 rawvideo -> numpy 按 t=i/fps 精确取当前字幕 -> 合成字幕带 -> 重新编码。
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
from PIL import Image


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAILED:", " ".join(cmd)[:300])
        print(r.stderr[-2000:])
        sys.exit(1)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--timeline", default="timeline.json")
    ap.add_argument("--anim", default="anim")
    ap.add_argument("--build", default="build")
    ap.add_argument("--audio", default="narration.mp3")
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--anim-dur", type=float, default=4.0, help="每页实际渲染的动效秒数")
    ap.add_argument("--band-y", type=int, default=1500)
    ap.add_argument("--band-h", type=int, default=420)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--out", default="build/final.mp4")
    ap.add_argument("--crf", default="18")
    args = ap.parse_args()

    BASE = pathlib.Path(args.base).expanduser().resolve()
    ANIM = BASE / args.anim
    OUT = BASE / args.build
    OUT.mkdir(parents=True, exist_ok=True)
    W, H, FPS = args.width, args.height, args.fps
    BAND_Y, BAND_H = args.band_y, args.band_h

    tl = json.load(open(BASE / args.timeline))
    pages, subs, TOTAL = tl["pages"], tl["subs"], tl["total"]

    # ---------- 1. 每页 -> 视频（只渲染前 anim-dur 秒，其余复制末帧） ----------
    page_files = []
    for p in pages:
        n = p["page"]
        dur = round(p["end"] - p["start"], 3)
        out = OUT / f"page{n:02d}.mp4"
        pad = max(0.0, dur - args.anim_dur)
        vf = f"tpad=stop_mode=clone:stop_duration={pad:.3f}"
        run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
             "-i", str(ANIM / f"frames/p{n:02d}/f%04d.png"),
             "-vf", vf, "-t", f"{dur:.3f}",
             "-c:v", "libx264", "-preset", "medium", "-crf", args.crf, "-pix_fmt", "yuv420p",
             str(out)])
        page_files.append(out)
        print(f"page{n:02d}  {dur:.2f}s")

    # ---------- 2. 拼接 ----------
    lst = OUT / "concat.txt"
    lst.write_text("".join(f"file '{f.name}'\n" for f in page_files))
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(OUT / "video_raw.mp4")])
    print("concat ok")

    # ---------- 3. 预载字幕 alpha ----------
    cache = {}
    for s in subs:
        p = ANIM / "subs" / ("sub%03d.png" % s["i"])
        if not p.exists():
            continue
        im = Image.open(p).convert("RGBA")
        if im.size != (W, BAND_H):
            im = im.resize((W, BAND_H), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32)
        cache[s["i"]] = (a[:, :, :3], a[:, :, 3:4] / 255.0)
    missing = len(subs) - len(cache)
    print("字幕缓存", len(cache), "缺失", missing)

    total_frames = int(round(TOTAL * FPS))
    frame_sub = [None] * total_frames
    for s in subs:
        if s["i"] not in cache:
            continue
        a = int(round(s["start"] * FPS))
        b = int(round(s["end"] * FPS))
        for f in range(max(0, a), min(total_frames, b)):
            frame_sub[f] = s["i"]
    print("总帧数", total_frames, "有字幕帧", sum(1 for x in frame_sub if x is not None))

    # ---------- 4. 逐帧合成 ----------
    audio = BASE / args.audio
    cmd_enc = ["ffmpeg", "-y", "-v", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if audio.exists():
        cmd_enc += ["-i", str(audio), "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd_enc += ["-c:v", "libx264", "-preset", "medium", "-crf", args.crf,
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(BASE / args.out)]

    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(OUT / "video_raw.mp4"),
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(cmd_enc, stdin=subprocess.PIPE)

    fsize = W * H * 3
    n = 0
    t0 = time.time()
    while True:
        buf = dec.stdout.read(fsize)
        if len(buf) < fsize:
            break
        frame = np.frombuffer(buf, dtype=np.uint8).reshape(H, W, 3).copy()
        si = frame_sub[n] if n < total_frames else None
        if si is not None:
            rgb, alpha = cache[si]
            band = frame[BAND_Y:BAND_Y + BAND_H].astype(np.float32)
            band = band * (1.0 - alpha) + rgb * alpha
            frame[BAND_Y:BAND_Y + BAND_H] = np.clip(band, 0, 255).astype(np.uint8)
        enc.stdin.write(frame.tobytes())
        n += 1
        if n % 500 == 0:
            print(f"  {n}/{total_frames}  {(time.time() - t0):.0f}s", flush=True)

    enc.stdin.close()
    dec.wait()
    enc.wait()
    print("done, frames", n)

    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
                        "-show_entries", "stream=codec_type,width,height", "-of", "default=nw=1",
                        str(BASE / args.out)], capture_output=True, text=True)
    print(r.stdout)


if __name__ == "__main__":
    main()
