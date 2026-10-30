# Vertical Talking-Head Video Kit · sjbxsp-kit

[中文](README.md) | **English**

The full pipeline that turns "one idea" into a 1080×1920 vertical video: animated card slides, one-shot voice-over, and burned-in white-on-black subtitles. Both halves are included — the writing skills and the render engine.

Packed: 2026-10-30

## What's inside

```
sjbxsp-kit/
└── skills/
    ├── sjbxsp/            Render engine: animated cards + voice-over + subtitles + cover
    ├── SJBXWA/            Writing ① Structuring: reshape rambling speech into scannable copy
    └── lead-media-script/ Writing ② Scripting: turn a topic or raw material into a record-ready script
```

- **sjbxsp** (208K): 10–14 animated card pages, a single-pass voice-over, frame-accurate subtitle sync, and a 3:4 cover with a two-layer safe area. Ships 6 scripts (render / align / gen_subs / compose / make_cover plus 3 `.mjs` templates), 6 reference docs and 3 case studies.
- **SJBXWA** (16K): rewrites structure and rhythm only — never touches the argument or the numbers. Best for "this reads like a mess, make it clear".
- **lead-media-script** (40K): registered as "Lead-自媒体口播文案". Produces 3 opening candidates, titles and cover copy, recording notes and a self-check list. Best for "I only have an idea, write me something I can read out loud".

How they chain: **write first (SJBXWA to tidy, lead-media-script to draft) → then hand the script to sjbxsp**. Step 1 of sjbxsp is "lock the script" — the script is the foundation of the whole video, and any rewrite means re-running alignment and compositing.

## Install

```bash
git clone <this-repo>.git
cp -R sjbxsp-kit/skills/* ~/.workbuddy/skills/
```

Or use the bundled script:

```bash
./install.sh
```

After restarting the session, phrases like "make a video", "talking-head video", "turn this script into a video" will trigger the skill, or you can call `sjbxsp` by name.

## Dependencies

All of these must be callable from the command line.

| Dependency | Purpose | Check |
|---|---|---|
| `ffmpeg` / `ffprobe` | compositing, concatenation, audio mixing (no libass needed — subtitles are composited as per-frame alpha PNGs) | `ffmpeg -version` |
| Python 3 + `numpy`, `Pillow` | align / gen_subs / compose / make_cover | `python -c "import numpy,PIL"` |
| `whisper` (faster-whisper) | word-level timestamps — all subtitles and the page timeline are derived from it | `whisper --help` |
| `ego-browser` | CDP frame capture (card frames, subtitle PNGs, cover master) | `which ego-browser` |
| Node (bundled with ego-browser) | runs the generated `.mjs` capture scripts | — |

Models: put whisper models in `~/Models/whisper/`. In mainland China, set `HF_ENDPOINT=https://hf-mirror.com` when downloading.

## Minimal end-to-end run

```bash
# 0. Finalise speech.txt (Chinese numerals, Chinese units, no timecodes, second person, blank line between paragraphs)
# 1. Generate the voice-over in ONE pass → narration.mp3 (never per-sentence TTS)
whisper narration.mp3 -m medium -l zh --word-timestamps -o asr --output-format json
python <skill>/scripts/align.py --base <project> --split-first 4
# 2. Build the cards: screenshot the re-drawn UI first, then lay out slides.html (see references/layout-rules.md)
python <skill>/scripts/render.py frames --base <project> --pages <page-count>
python <skill>/scripts/gen_subs.py --base <project>
ego-browser nodejs < <project>/anim/render_subs.mjs
python <skill>/scripts/compose.py --base <project> --audio narration.mp3
# 3. Cover
python <skill>/scripts/render.py cover-hd --base <project>
python <skill>/scripts/make_cover.py --base <project> --src anim/cover-hd.png
```

The full 10-step workflow, hard rules and QA checklist live in `skills/sjbxsp/SKILL.md` (Chinese).

## Three things to adjust on a new machine

1. **Python interpreter path**: the "Dependencies" section of `sjbxsp/SKILL.md` hardcodes the original author's venv path. Point it at your own — the scripts themselves contain no hardcoded paths.
2. **Project paths in case studies**: line 4 of each `sjbxsp/cases/*.md` records the original project directory. Documentation only, does not affect execution.
3. **Publishing**: `references/publish-video.md` documents an internal CMS publishing flow (captcha login, form-field mapping pitfalls). Ignore that section entirely if you do not use it — the default deliverable is just the mp4 plus the cover image, no upload.

## Core hard rules at a glance

- 1080×1920, 25fps, mp4 (h264 + aac + faststart).
- At most 0–1 raw UI screenshots per video, default 0; dashboards, forms, chats and web pages are always re-drawn.
- Any segment explaining rhythm, camera position, UI or the final look must use original footage; real footage should cover 20–35% of the video.
- Subtitles: white text, 4px black outline, max two lines, content area ends at y=1600.
- Every number needs its basis and unit; estimates must state the assumption.
- Cover safe area is two-layered: the 3:4 crop region (y 240–1680) plus another 92px inset on all four sides; upload version at least 1080px wide.
- Pick a new theme colour for every video — never reuse the previous one.

## License

No license file is included; all rights reserved. Add one (e.g. MIT) if you intend to open-source it.

---

> Note: all skill content (`SKILL.md`, references, case studies) is written in Chinese. This English README describes the kit; the workflows themselves assume a Chinese-language workflow.
