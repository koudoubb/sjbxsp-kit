#!/usr/bin/env python3
"""把每条字幕做「两行均衡断行」，并生成逐条渲染透明 PNG 的 ego-browser 脚本。

用法：
  python gen_subs.py --base <项目目录> [--timeline timeline.json]
                     [--subtitle anim/subtitle.html] [--out anim/render_subs.mjs]
                     [--maxw 16.2]

断行规则（三类重罚，缺一不可）：
  1. 不在「数字 + 量词」之间断（五|条）
  2. 不在常用双字词中间断（就|是、频道）
  3. 不在英文单词内部断（Tyle|r、Inside China L|ives）
"""
import argparse
import json
import pathlib

DIGITS = set("零一二三四五六七八九十百千万亿0123456789")
MEASURE = set("条个万位次年月天秒分块元美")
BAD_PAIRS = set("""就是 也是 不是 还是 但是 可是 可以 这个 那个 一个 没有 因为 所以 如果
已经 他们 我们 你们 时候 现在 其实 然后 或者 而且 以及 比较 非常 东西 一起 这种 那种
什么 怎么 这样 那样 自己 别人 觉得 知道 认为 需要 地方 事情 问题 内容 视频 频道 收益
拍摄 剪辑 搭档 合作 孵化 只有 可以 应该 一直 一定 表示 因为 由于 关于 对于""".split())


def is_cn(ch):
    return "\u4e00" <= ch <= "\u9fff"


def dispw(t):
    return sum(1.0 if is_cn(ch) else 0.55 for ch in t)


def balance(text, maxw):
    text = text.strip()
    if dispw(text) <= maxw:
        return text
    n = len(text)
    best = None
    for i in range(1, n):
        left, right = text[:i], text[i:]
        if dispw(left) > maxw or dispw(right) > maxw:
            continue
        score = abs(dispw(left) - dispw(right))
        if text[i - 1] in "，、；：,;:":
            score -= 1.6
        if text[i] in " \u3000":
            score -= 1.0
        if dispw(right) < 4:          # 末行孤字
            score += 3
        if text[i - 1] in DIGITS and text[i] in MEASURE:
            score += 12               # 数字 + 量词
        if (text[i - 1] + text[i]) in BAD_PAIRS:
            score += 12               # 常用双字词
        if (text[i - 1].isascii() and text[i].isascii()
                and text[i - 1].isalnum() and text[i].isalnum()):
            score += 30               # 英文单词内部
        if best is None or score < best[0]:
            best = (score, i)
    if best:
        i = best[1]
        return text[:i] + "<br>" + text[i:]
    return text


TEMPLATE = """// 自动生成：逐条字幕渲染为透明 PNG（1080 x {band_h}）
const task = await taskSpace("sjbxsp subs");
const page = task.page("p1");
await page.cdp("Emulation.setDeviceMetricsOverride", {{ width: 1080, height: {band_h}, deviceScaleFactor: 1, mobile: false }});
await page.cdp("Emulation.setDefaultBackgroundColorOverride", {{ color: {{ r: 0, g: 0, b: 0, a: 0 }} }});
await page.goto("file://{subtitle}");
await page.waitForLoadState("load");
await page.waitForTimeout(1200);

const texts = [{body}];
const dir = "{outdir}";
const t0 = Date.now();
for (let i = 0; i < texts.length; i++) {{
  await page.evaluate((t) => window.setText(t), texts[i]);
  await page.waitForTimeout(40);
  await page.screenshot({{ path: `${{dir}}/sub${{String(i).padStart(3, "0")}}.png`, scale: "css" }});
}}
console.log("subs done", texts.length, ((Date.now() - t0) / 1000).toFixed(1), "s");
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--timeline", default="timeline.json")
    ap.add_argument("--subtitle", default="anim/subtitle.html")
    ap.add_argument("--out", default="anim/render_subs.mjs")
    ap.add_argument("--subdir", default="anim/subs")
    ap.add_argument("--maxw", type=float, default=16.2, help="一行可容纳的显示宽度")
    ap.add_argument("--band-h", type=int, default=420, help="字幕带高度，需与 compose 一致")
    args = ap.parse_args()

    BASE = pathlib.Path(args.base).expanduser().resolve()
    subs = json.load(open(BASE / args.timeline))["subs"]

    lines = []
    two = 0
    for s in subs:
        txt = s["text"].replace("\n", "")
        b = balance(txt, args.maxw)
        if "<br>" in b:
            two += 1
        lines.append(json.dumps(b, ensure_ascii=False))

    js = TEMPLATE.format(
        band_h=args.band_h,
        subtitle=str(BASE / args.subtitle),
        body="\n  " + ",\n  ".join(lines),
        outdir=str(BASE / args.subdir),
    )
    out = BASE / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(js)
    print(f"subs {len(subs)}  两行 {two}  写入 {out}")


if __name__ == "__main__":
    main()
