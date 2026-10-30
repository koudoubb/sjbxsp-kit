#!/usr/bin/env python3
"""导出 3:4 视频封面：从高清母版裁安全区，输出大图母版 + 上传版。

用法：
  # 推荐：先渲 2x 母版，再裁（文字最锐）
  SJBX_BASE=<project> ego-browser nodejs < render_cover_hd.mjs
  python make_cover.py --base <project> --src anim/cover-hd.png

  # 兜底：直接从成片抽帧（1x 分辨率）
  python make_cover.py --base <project> --src build/final.mp4 --at 1.5

参数：
  --top / --height  3:4 安全区在 1080x1920 里的位置，默认 240 / 1440
  --up-width        上传版宽度，默认 1080（**不要再出 500 宽，平台放大会发虚**）
  --dpr             母版相对 1080x1920 的倍率；不填则按图宽自动推断

产物：
  cover-3x4-<W>x<H>.png    母版（与母版同分辨率，留档/备用）
  video-cover-<w>x<h>.jpg  上传版（默认 1080x1440，质量 95 无色度抽样）
"""
import argparse
import pathlib
import subprocess
import sys

from PIL import Image

BASE_W = 1080
BASE_H = 1920


def edges_are_black(im, band=4, thresh=14.0):
    """检测裁切图四边是否为纯黑——出现黑边说明裁切区落到了卡片背景之外。"""
    g = im.convert("L")
    w, h = g.size
    strips = [
        g.crop((0, 0, w, band)),
        g.crop((0, h - band, w, h)),
        g.crop((0, 0, band, h)),
        g.crop((w - band, 0, w, h)),
    ]
    means = []
    for s in strips:
        px = list(s.getdata())
        means.append(sum(px) / max(1, len(px)))
    return min(means) < thresh, [round(m, 1) for m in means]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--src", default="anim/cover-hd.png", help="高清母版 png 或成片 mp4")
    ap.add_argument("--at", type=float, default=1.5, help="src 是 mp4 时的抽帧时间点")
    ap.add_argument("--top", type=int, default=240, help="3:4 区顶边 y（1080x1920 坐标）")
    ap.add_argument("--height", type=int, default=1440)
    ap.add_argument("--dpr", type=int, default=0, help="母版倍率，0=自动推断")
    ap.add_argument("--up-width", type=int, default=1080, help="上传版宽度")
    ap.add_argument("--out", default="", help="母版文件名，默认 cover-3x4-<W>x<H>.png")
    ap.add_argument("--upload", default="", help="上传版文件名，默认 video-cover-<w>x<h>.jpg")
    args = ap.parse_args()

    BASE = pathlib.Path(args.base).expanduser().resolve()
    src = BASE / args.src
    if not src.exists():
        print(f"src 不存在：{src}")
        sys.exit(1)

    # 取图：mp4 抽帧，或直接读 png
    if src.suffix.lower() in (".mp4", ".mov", ".mkv"):
        frame = BASE / "_cover_frame.png"
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(args.at),
                            "-i", str(src), "-frames:v", "1", str(frame)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-600:])
            sys.exit(1)
        im = Image.open(frame).convert("RGB")
    else:
        im = Image.open(src).convert("RGB")

    W, H = im.size
    dpr = args.dpr or max(1, round(W / BASE_W))
    if abs(W - BASE_W * dpr) > 4:
        print(f"警告：母版宽 {W} 与 {BASE_W}×{dpr} 不符，仍按 dpr={dpr} 处理")

    box = (0, args.top * dpr, W, min(H, (args.top + args.height) * dpr))
    cov = im.crop(box)

    out_name = args.out or f"cover-3x4-{cov.width}x{cov.height}.png"
    cov.save(BASE / out_name)

    up_w = args.up_width
    up_h = round(up_w * cov.height / cov.width)
    up = cov.resize((up_w, up_h), Image.LANCZOS)
    up_name = args.upload or f"video-cover-{up_w}x{up_h}.jpg"
    up.save(BASE / up_name, quality=95, subsampling=0)

    print(f"母版      {W}x{H} (dpr={dpr})  ->  {out_name}  {cov.width}x{cov.height}")
    print(f"上传版    {up_w}x{up_h}  ->  {up_name}")

    black, means = edges_are_black(cov)
    print(f"四边亮度  {means}  {'← 有黑边，先修卡片背景/安全区' if black else 'OK'}")
    if up_w < BASE_W:
        print(f"警告：上传版宽 {up_w} 小于成片宽 {BASE_W}，平台放大后会发虚，建议 1080")
    if black:
        sys.exit(2)
    print("提示：确认第一页元素在安全区内还留了内边距 → python render.py safe --base <project>")


if __name__ == "__main__":
    main()
