#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Собирает вертикальные 720×1280 shorts из mp3-озвучек.
• фон — случайная картинка Unsplash («finance, money»);
  при 503 / timeout → до 5 повторов, затем однотонный fallback.
• текст берётся из scripts/lines.txt (строка = субтитр).
"""

import math, random, subprocess, time, hashlib, sys
from pathlib import Path
from io import BytesIO

import httpx
from PIL import Image
import mutagen

# ─ конфигурация ──────────────────────────────────────────────────────────
MAX_CLIPS   = 2                                  # сколько роликов за ран
FONT        = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SIZE   = 54
TEXT_COLOR  = "white"

BG_CACHE = Path("assets/bg")                     # кеш фонов
BG_CACHE.mkdir(parents=True, exist_ok=True)
VOICE_DIR = Path("scripts/audio")                # mp3-файлы
OUT_DIR   = Path("videos")
OUT_DIR.mkdir(exist_ok=True)
# ─────────────────────────────────────────────────────────────────────────

mp3_files = sorted(VOICE_DIR.glob("voice_*.mp3"))[:MAX_CLIPS]
if not mp3_files:
    sys.exit("❌  Нет voice_*.mp3 в scripts/audio/ — запустите cut_highlights.py")

lines = (Path("scripts/lines.txt")
         .read_text(encoding="utf-8")
         .splitlines())[:len(mp3_files)]

# ─ вспомогательные функции ──────────────────────────────────────────────
def solid_bg(color="#222831") -> Path:
    """Однотонный запасной фон."""
    dst = BG_CACHE / f"solid_{color.lstrip('#')}.jpg"
    if not dst.exists():
        Image.new("RGB", (720, 1280), color).save(dst, "JPEG", quality=85)
    return dst

def fetch_bg() -> Path:
    """720×1280 картинка из кеша или Unsplash; fallback — solid_bg()."""
    query  = ",".join(random.sample(
        ["finance", "money", "budget", "investment", "cash"], 2))
    url    = f"https://source.unsplash.com/720x1280/?{query}"
    key    = hashlib.md5(url.encode()).hexdigest()[:12] + ".jpg"
    target = BG_CACHE / key
    if target.exists():
        return target

    for attempt in range(1, 6):
        try:
            r = httpx.get(url, timeout=15)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).convert("RGB")
            img.resize((720, 1280), Image.LANCZOS).save(target, "JPEG", quality=90)
            return target
        except Exception as e:
            wait = attempt * 2
            print(f"⚠️  {e} — повтор через {wait}s ({attempt}/5)")
            time.sleep(wait)

    print("⚠️  Unsplash недоступен — использую однотонный фон")
    return solid_bg()

# ─ основная петля ────────────────────────────────────────────────────────
for mp3, caption in zip(mp3_files, lines):
    duration = math.ceil(mutagen.File(mp3).info.length) + 1
    bg       = fetch_bg()
    out      = OUT_DIR / mp3.with_suffix(".mp4").name   # voice_1.mp4 …

    # экранируем drawtext-спецсимволы
    safe = (caption
            .replace("\\", r"\\").replace(":", r"\:")
            .replace("'",  r"\'").replace('"', r'\"'))

    draw_filter = (
        f"[0:v]scale=720:1280,format=yuv420p[v0];"
        f"[v0]drawtext=fontfile={FONT}:"
        f"text='{safe}':fontcolor={TEXT_COLOR}:fontsize={FONT_SIZE}:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:"
        f"box=1:boxcolor=black@0.55:boxborderw=14"
    )

    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-loop", "1", "-i", str(bg),   # 0:v
        "-i", str(mp3),                # 1:a
        "-filter_complex", draw_filter,
        "-t", str(duration),
        "-map", "[v0]", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(out)
    ]
    subprocess.run(cmd, check=True)
    print(f"🎞️  {out.name}  | фон: {bg.name} | длительность ≈ {duration}s")
    time.sleep(1)   # чтобы не бушевать Unsplash
