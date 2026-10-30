#!/usr/bin/env python3
"""把 ASR 词级时间戳对齐到口播原文，产出字幕条目 + 页面时间轴。

用法：
  python align.py --base <项目目录> [--asr asr/narration.json]
                  [--script speech.txt] [--out timeline.json]
                  [--split-first N]

--split-first N  第一段拆成 N 页（封面/引入页），其余每段 1 页。默认 4。

输出 timeline.json：{"subs": [...], "pages": [...], "total": 秒}

关键设计（改动前务必读 references/pitfalls.md）：
  * 全局 difflib 字符映射给初值，**直接采用**，只做单调/不重叠截断；
    不要做「时间窗内重匹配」，会把已经对的英文/数字处改坏。
  * 不做游标式顺序对齐，会累积漂移。
"""
import argparse
import bisect
import difflib
import json
import pathlib
import re


def is_cn(ch):
    return "\u4e00" <= ch <= "\u9fff"


def is_alnum(ch):
    return ch.isalnum()


def dispw(t):
    """显示宽度：中文 1，其他 0.55"""
    return sum(1.0 if is_cn(ch) else 0.55 for ch in t)


def build_asr_stream(asr):
    chars, times = [], []
    for seg in asr["segments"]:
        for w in seg.get("words", []):
            word = w["word"]
            n = sum(1 for c in word if is_cn(c) or is_alnum(c))
            if n == 0:
                continue
            step = (w["end"] - w["start"]) / n
            k = 0
            for c in word:
                if is_cn(c) or is_alnum(c):
                    chars.append(c.lower())
                    times.append((w["start"] + step * k, w["start"] + step * (k + 1)))
                    k += 1
    return chars, times


def split_text(s, maxw):
    """按标点切分，单条不超过 maxw 个中文宽（= 两行容量）"""
    s = s.strip()
    if dispw(s) <= maxw:
        return [s]
    clauses = [x for x in re.split(r"(?<=[，、；：])", s) if x]
    chunks, cur = [], ""
    for c in clauses:
        if dispw(cur + c) <= maxw:
            cur += c
        else:
            if cur:
                chunks.append(cur)
                cur = ""
            if dispw(c) <= maxw:
                cur = c
            else:
                toks = re.findall(r"[A-Za-z0-9\.%]+|.", c)
                line = ""
                for tk in toks:
                    if dispw(line + tk) <= maxw:
                        line += tk
                    else:
                        if line:
                            chunks.append(line)
                        line = tk
                if line:
                    cur = line
    if cur:
        chunks.append(cur)
    out = []
    for c in chunks:
        if out and dispw(c) < 6 and dispw(out[-1] + c) <= maxw:
            out[-1] += c
        else:
            out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="项目目录")
    ap.add_argument("--asr", default="asr/narration.json", help="whisper JSON（相对 base）")
    ap.add_argument("--script", default="speech.txt", help="口播原文（相对 base）")
    ap.add_argument("--out", default="timeline.json", help="输出（相对 base）")
    ap.add_argument("--split-first", type=int, default=4, help="第一段拆几页")
    ap.add_argument("--maxw", type=float, default=29.0, help="单条字幕最大显示宽度")
    args = ap.parse_args()

    BASE = pathlib.Path(args.base).expanduser().resolve()
    asr = json.load(open(BASE / args.asr))
    text = (BASE / args.script).read_text().strip()

    achars, atimes = build_asr_stream(asr)

    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    sentences = []
    for pi, p in enumerate(paras):
        for s in re.split(r"(?<=[。！？])", p):
            s = s.strip()
            if s:
                sentences.append((pi, s))

    entries = []
    for si, (pi, s) in enumerate(sentences):
        for c in split_text(s, args.maxw):
            entries.append((pi, si, c))

    # 句内过短条目合并（不跨句）
    merged = []
    for pi, si, c in entries:
        if merged and merged[-1][1] == si and dispw(merged[-1][2]) < 12 and dispw(merged[-1][2] + c) <= args.maxw:
            merged[-1] = (pi, si, merged[-1][2] + c)
        else:
            merged.append((pi, si, c))
    entries = merged

    bchars, bidx = [], []
    for i, (pi, si, c) in enumerate(entries):
        for ch in c:
            if is_cn(ch) or is_alnum(ch):
                bchars.append(ch.lower())
                bidx.append(i)

    sm = difflib.SequenceMatcher(a=achars, b=bchars, autojunk=False)
    b2time = {}
    for block in sm.get_matching_blocks():
        for k in range(block.size):
            b2time[block.b + k] = atimes[block.a + k]
    order = sorted(b2time.keys())

    def rough_time(bi):
        if bi in b2time:
            return b2time[bi][0]
        lo = max([k for k in order if k < bi], default=None)
        hi = min([k for k in order if k > bi], default=None)
        if lo is None and hi is None:
            return 0.0
        if lo is None:
            return b2time[hi][0]
        if hi is None:
            return b2time[lo][0]
        t0, t1 = b2time[lo][0], b2time[hi][0]
        return t0 + (t1 - t0) * (bi - lo) / (hi - lo)

    def rough_span(bi):
        if bi in b2time:
            return b2time[bi]
        lo = max([k for k in order if k < bi], default=None)
        hi = min([k for k in order if k > bi], default=None)
        if lo is None and hi is None:
            return (0.0, 0.0)
        if lo is None:
            return b2time[hi]
        if hi is None:
            return b2time[lo]
        t0s, t0e = b2time[lo]
        t1s, t1e = b2time[hi]
        r = (bi - lo) / (hi - lo)
        return (t0s + (t1s - t0s) * r, t0e + (t1e - t0e) * r)

    subs = []
    for i, (pi, si, c) in enumerate(entries):
        q = "".join(ch.lower() for ch in c if is_cn(ch) or is_alnum(ch))
        if not q:
            continue
        idxs = [j for j, s_i in enumerate(bidx) if s_i == i]
        if not idxs:
            continue
        t_rough = rough_time(idxs[0])
        t0 = t_rough
        t1 = rough_span(idxs[-1])[1]
        if t1 <= t0 + 0.4:
            t1 = t0 + max(0.9, len(q) / 4.6)
        subs.append({
            "i": len(subs), "para": pi, "sent": si,
            "start": round(max(0.0, t0 - 0.05), 2),
            "end": round(t1 + 0.14, 2), "text": c,
            "rough": round(t_rough, 2),
        })

    # 单调 + 不重叠 + 最短 0.55s
    for i in range(1, len(subs)):
        if subs[i]["start"] < subs[i - 1]["start"] + 0.25:
            subs[i]["start"] = round(subs[i - 1]["start"] + 0.25, 2)
    for i in range(len(subs) - 1):
        if subs[i]["end"] > subs[i + 1]["start"]:
            subs[i]["end"] = subs[i + 1]["start"]
    subs[-1]["end"] = round(min(asr["duration"], subs[-1]["end"]), 2)
    for i, s0 in enumerate(subs):
        if s0["end"] - s0["start"] < 0.55:
            s0["end"] = round(min(asr["duration"], s0["start"] + 0.55), 2)
        s0["i"] = i

    first_sub_of_sent = {}
    for s0 in subs:
        first_sub_of_sent.setdefault(s0["sent"], s0)
    para_first_sent = {}
    for si, (pi, _) in enumerate(sentences):
        para_first_sent.setdefault(pi, si)

    n_first = min(args.split_first, len(sentences))
    page_start_sents = list(range(n_first)) + [
        para_first_sent[p] for p in sorted(para_first_sent) if p >= 1
    ]

    pages = []
    for k, si in enumerate(page_start_sents):
        sub = first_sub_of_sent.get(si)
        st = 0.0 if k == 0 else (round(max(0.0, sub["start"] - 0.12), 2) if sub else 0.0)
        pages.append({"page": k + 1, "start": st, "end": None})
    for k in range(len(pages) - 1):
        pages[k]["end"] = pages[k + 1]["start"]
    pages[-1]["end"] = round(asr["duration"], 2)

    json.dump({"subs": subs, "pages": pages, "total": asr["duration"]},
              open(BASE / args.out, "w"), ensure_ascii=False, indent=1)

    print("字幕条目", len(subs), "页数", len(pages), "总时长", round(asr["duration"], 2))
    for p in pages:
        print(f"  P{p['page']:02d}: {p['start']:7.2f} -> {p['end']:7.2f}  ({p['end'] - p['start']:5.1f}s)")
    over = [s0 for s0 in subs if dispw(s0["text"]) > args.maxw + 1.5]
    print("超宽条目", len(over))
    for s0 in over:
        print("  ", f"{s0['start']:.2f}", f"{dispw(s0['text']):.1f}w", s0["text"])
    drift = [abs(s0["start"] - s0["rough"]) for s0 in subs]
    print("与粗定位最大偏差 %.2fs" % (max(drift) if drift else 0))


if __name__ == "__main__":
    main()
