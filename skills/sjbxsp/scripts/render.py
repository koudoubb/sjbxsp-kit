#!/usr/bin/env python3
"""生成并执行 ego-browser 脚本（因为 ego-browser 的 node 环境拿不到环境变量）。

为什么需要这个壳：
  `ego-browser nodejs < x.mjs` 的 node 进程 cwd 固定为 "/"，process.env 只有十几个键，
  命令行参数也进不去（argv 里只有可执行文件路径）。所以路径、页数、倍率这些参数
  只能在**生成脚本时写死到正文里**。之前用 SJBX_BASE 等环境变量传参的写法全部失效。

子命令：
  frames    逐页渲染帧序列
            python render.py frames --base <project> --pages 12 [--from 1] [--fps 25] [--frames 100]
  safe      3:4 封面安全区核对（四边留白 < margin 时退出码 2）
            python render.py safe --base <project> [--page 1] [--margin 92]
  cover-hd  2 倍超采样渲封面母版
            python render.py cover-hd --base <project> [--page 1] [--scale 2] [--out anim/cover-hd.png]
"""
import argparse
import pathlib
import shutil
import subprocess
import sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
TPL = SKILL / "assets" / "tpl"


def fill(tpl_name, mapping):
    src = (TPL / tpl_name).read_text(encoding="utf-8")
    for k, v in mapping.items():
        src = src.replace(f"__{k}__", str(v))
    left = [ln for ln in src.splitlines() if "__" in ln and "__" not in ln.split("//")[0]]
    if left:
        print("警告：仍有未替换的占位符")
        for ln in left[:5]:
            print("  ", ln.strip()[:100])
    return src


def run_ego(text, base):
    build = base / "build"
    try:
        build.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # 沙箱 broker 会抛假 EEXIST，目录其实已存在
    script = build / "_sjbxsp_tmp.mjs"
    script.write_text(text, encoding="utf-8")
    if not shutil.which("ego-browser"):
        print("找不到 ego-browser 命令，确认已安装并在 PATH 里")
        sys.exit(1)
    with open(script, encoding="utf-8") as fh:
        r = subprocess.run(["ego-browser", "nodejs"], stdin=fh, cwd=str(base),
                           capture_output=True, text=True)
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    if out:
        print(out)
    if err:
        print(err[-1500:])
    try:
        script.unlink()
    except OSError:
        pass
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["frames", "safe", "cover-hd"])
    ap.add_argument("--base", required=True)
    ap.add_argument("--html", default="anim/slides.html")
    ap.add_argument("--pages", type=int, default=12)
    ap.add_argument("--from", dest="frm", type=int, default=1)
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--frames", type=int, default=100)
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--top", type=int, default=240)
    ap.add_argument("--height", type=int, default=1440)
    ap.add_argument("--margin", type=int, default=92)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--out", default="anim/cover-hd.png")
    args = ap.parse_args()

    base = pathlib.Path(args.base).expanduser().resolve()
    if not (base / args.html).exists():
        print(f"找不到 {base / args.html}")
        sys.exit(1)

    common = {"BASE": base, "HTML": args.html}

    if args.action == "frames":
        text = fill("render_frames.mjs.tpl", {
            **common, "PAGES": args.pages, "FROM": args.frm,
            "FPS": args.fps, "FRAMES": args.frames,
        })
        print(f"渲染第 {args.frm}–{args.pages} 页，每页 {args.frames} 帧 @ {args.fps}fps")
    elif args.action == "safe":
        text = fill("check_safe.mjs.tpl", {
            **common, "PAGE": args.page, "TOP": args.top,
            "HEIGHT": args.height, "MARGIN": args.margin,
        })
    else:
        text = fill("render_cover_hd.mjs.tpl", {
            **common, "PAGE": args.page, "SCALE": args.scale, "OUT": args.out,
        })

    sys.exit(run_ego(text, base))


if __name__ == "__main__":
    main()
