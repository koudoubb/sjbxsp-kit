#!/usr/bin/env bash
# 安装 sjbxsp-kit 到 WorkBuddy 用户级技能目录
# 默认目标：~/.workbuddy/skills  可用 WORKBUDDY_SKILLS_DIR 覆盖
# 已存在的同名技能不会删除，会先重命名为 <name>.bak-<时间戳>

set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${WORKBUDDY_SKILLS_DIR:-$HOME/.workbuddy/skills}"
STAMP="$(date +%Y%m%d%H%M%S)"

if [ ! -d "$SRC_DIR/skills" ]; then
  echo "找不到 skills/ 目录，请在仓库根目录执行" >&2
  exit 1
fi

mkdir -p "$DEST"
echo "目标目录：$DEST"

for d in "$SRC_DIR"/skills/*/; do
  name="$(basename "$d")"
  if [ -e "$DEST/$name" ]; then
    mv "$DEST/$name" "$DEST/$name.bak-$STAMP"
    echo "  已备份旧版：$name -> $name.bak-$STAMP"
  fi
  cp -R "$d" "$DEST/$name"
  echo "  已安装：$name"
done

echo
echo "完成。重启 WorkBuddy 会话后生效。"
echo "依赖检查："
for c in ffmpeg ffprobe whisper ego-browser; do
  if command -v "$c" >/dev/null 2>&1; then
    echo "  [ok] $c"
  else
    echo "  [缺] $c"
  fi
done
command -v python3 >/dev/null 2>&1 && python3 -c "import numpy, PIL" 2>/dev/null \
  && echo "  [ok] python numpy + Pillow" \
  || echo "  [缺] python numpy / Pillow"
