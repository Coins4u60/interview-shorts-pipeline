#!/usr/bin/env python3
"""
Собирает вертикальные 720×1280 шорты из audio/voice_*.mp3
Фон — случайная картинка Unsplash («finance, money») с кэшем.
"""

import math, random, subprocess, time, hashlib, sys
from pathlib import Path
from io import BytesIO
import httpx
from PIL import Image
import mutagen

MAX_CLIPS  = 2
FONT       = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SIZE  = 64
TEXT_COLOR = "white"

BG_CACHE = Path(__file__).parent / "assets" / "bg"; BG_CACHE.mkdir(parents=True, exist_ok=True)

VOICE_DIR = Path(__file__).parent / "audio"
mp3_files = sorted(VOICE_DIR.glob("voice_*.mp3"))[:MAX_CLIPS]
if not mp3_files:
    sys.exit("❌ Нет audio/voice_*.mp3 — сначала cut_highlights.py")

lines = (Path("scripts/lines.txt").read_text("utf-8").splitlines())[:len(mp3_files)]

def solid(color="#222831"):
    dst = BG_CACHE / f"solid_{color[1:]}.jpg"
    if not dst.exists():
        Image.new("RGB", (720,1280), color).save(dst, "JPEG", quality=80)
    return dst

def fetch_bg():
    q = ",".join(random.sample(["finance","money","budget","investment","cash"],2))
    url = f"https://source.unsplash.com/720x1280/?{q}"
    dst = BG_CACHE / (hashlib.md5(url.encode()).hexdigest()[:12]+".jpg")
    if dst.exists(): return dst
    for k in range(5):
        try:
            r = httpx.get(url, timeout=20); r.raise_for_status()
            Image.open(BytesIO(r.content)).convert("RGB").resize((720,1280),Image.LANCZOS).save(dst,"JPEG",quality=90)
            return dst
        except Exception as e:
            print(f"⚠️ {e} — повтор через {k+1}s ({k+1}/5)"); time.sleep(k+1)
    print("⚠️ Unsplash недоступен, беру solid")
    return solid()

OUT = Path(__file__).parent / "videos"; OUT.mkdir(exist_ok=True)

for mp3, text in zip(mp3_files, lines):
    dur = math.ceil(mutagen.File(mp3).info.length)+1
    bg  = fetch_bg()
    out = OUT / mp3.with_suffix(".mp4").name
    safe = (text.replace("\\","\\\\").replace(":","\\:").replace("'","\\'").replace('"','\\"'))
    draw = (f"drawtext=fontfile={FONT}:text='{safe}':fontcolor={TEXT_COLOR}:"
            f"fontsize={FONT_SIZE}:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.5:boxborderw=10")
    cmd = ["ffmpeg","-y","-loop","1","-i",str(bg),"-i",str(mp3),
           "-filter_complex",draw,"-t",str(dur),
           "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k",
           "-shortest",str(out)]
    subprocess.run(cmd, check=True)
    print("🎞️", out.name, "(фон", bg.name, ")")
    time.sleep(1)
