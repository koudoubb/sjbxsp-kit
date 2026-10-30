# 口播视频工具包 · sjbxsp-kit

**中文** | [English](README_EN.md)

把「一句想法」做成「1080×1920 竖版动态卡片口播视频」的完整链路，写作与成片两段都在包里。

打包时间：2026-10-30

## 包里有什么

```
sjbxsp-kit/
└── skills/
    ├── sjbxsp/            成片引擎：动态卡片 + 配音 + 白字黑边字幕 + 封面
    ├── SJBXWA/            写作① 文案结构化：把流水口述改成工整、可扫读的条目文案
    └── lead-media-script/ 写作② 口播稿创作：从选题/素材写出能直接开口录的逐字稿
```

- **sjbxsp**（208K）：10–14 页动态卡片、整篇一次性配音、逐帧对齐字幕、3:4 封面双层安全区。脚本 5 个（render / align / gen_subs / compose / make_cover）+ 3 个 `.mjs` 模板、参考文档 4 篇、案例 3 份。
- **SJBXWA**（16K）：只改结构与语感，不动观点和数字。适合「这段读起来乱，帮我理清楚」。
- **lead-media-script**（40K）：`SKILL.md` 里的技能名是「Lead-自媒体口播文案」，含 3 个开头候选、标题封面、录制提示、自检。适合「只有一个想法，要写成能录的稿」。

三者的关系：**先写稿（SJBXWA 整理 / lead-media-script 起草）→ 再进 sjbxsp 出片**。sjbxsp 的第一步就是「口播稿定稿」，稿子是整片地基，改稿等于重跑对齐与合成。

## 安装

```bash
git clone https://github.com/koudoubb/sjbxsp-kit.git
cp -R sjbxsp-kit/skills/* ~/.workbuddy/skills/
```

或直接跑仓库里的脚本：

```bash
./install.sh
```

重启会话后即可通过「做视频」「口播视频」「把这篇稿子做成视频」等话术触发；也可以直接点名 `sjbxsp`。

## 依赖（缺一不可，且要能命令行直接调用）

| 依赖 | 用途 | 检查 |
|---|---|---|
| `ffmpeg` / `ffprobe` | 合成、拼接、混音（本机构建无 libass，字幕走逐帧 alpha，不依赖 libass） | `ffmpeg -version` |
| Python 3 + `numpy`、`Pillow` | align / gen_subs / compose / make_cover | `python -c "import numpy,PIL"` |
| `whisper`（faster-whisper） | 词级时间戳，字幕与时间轴全部由它派生 | `whisper --help` |
| `ego-browser` | CDP 逐帧截图（卡片帧、字幕 PNG、封面母版） | `which ego-browser` |
| Node（ego-browser 自带） | 执行生成的 `.mjs` 截图脚本 | — |

模型：whisper 模型放 `~/Models/whisper/`，国内拉模型需要 `HF_ENDPOINT=https://hf-mirror.com`。

## 最小跑通流程

```bash
# 0. 定稿 speech.txt（数字用汉字、单位用中文、不写时间码、人称统一「你」、段落空行）
# 1. 整篇一次生成配音 → narration.mp3（不要逐句合成）
whisper narration.mp3 -m medium -l zh --word-timestamps -o asr --output-format json
python <skill>/scripts/align.py --base <project> --split-first 4
# 2. 写卡片：先出重绘界面图，再排 slides.html（版式见 references/layout-rules.md）
python <skill>/scripts/render.py frames --base <project> --pages <页数>
python <skill>/scripts/gen_subs.py --base <project>
ego-browser nodejs < <project>/anim/render_subs.mjs
python <skill>/scripts/compose.py --base <project> --audio narration.mp3
# 3. 封面
python <skill>/scripts/render.py cover-hd --base <project>
python <skill>/scripts/make_cover.py --base <project> --src anim/cover-hd.png
```

完整 10 步、硬规则、自检清单全在 `skills/sjbxsp/SKILL.md`。

## 换机器时要注意的三处

1. **Python 解释器路径**：`sjbxsp/SKILL.md` 的「依赖」一节写的是原作者机器的 venv 绝对路径，换成自己的环境即可，脚本本身不含硬编码路径。
2. **案例里的项目目录**：`sjbxsp/cases/*.md` 第 4 行记录了原项目绝对路径，仅作记录，不影响执行。
3. **发布环节**：`SKILL.md` 第 10 步只保留了发布到内容后台的两条通用经验（表单字段别多塞、上传是追加行为），具体后台操作细节不在公开范围。默认交付物只有 mp4 + 封面图。

## 核心硬规则速览

- 1080×1920 / 25fps / mp4（h264 + aac + faststart）。
- 原片 UI 截图每支片 0–1 张，默认 0 张；后台/表单/聊天/网页一律重绘。
- 讲节奏、机位、界面、成片效果的段落必须用原片影像，全片实拍占比 20–35%。
- 字幕白字黑边 4px、最多两行、内容区到 y=1600 为止。
- 每个数字必须带口径与单位，估算值标注依据。
- 封面双层安全区：3:4 裁切区（y 240–1680）+ 四边再内缩 92px；上传版 ≥1080 宽。
- 每支片重新定主题色，不沿用上一支。

## License

未附带 License 文件，版权归作者所有。如需开源，自行添加（如 MIT）。
