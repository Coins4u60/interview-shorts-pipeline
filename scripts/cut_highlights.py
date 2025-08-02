#!/usr/bin/env python3
"""
Ищет в каталоге input/ *.mp4 (длинное интервью),
режет на хайлайты ≈ 60 ±5 секунд, кладёт как
scripts/audio/voice_*.mp3  (для build_video.py).
"""

import subprocess, random, shutil, os, re
from pathlib import Path

IN_DIR   = Path("input")           # сюда клади исходники
OUT_DIR  = Path("scripts/audio")   # mp3 для шортов
OUT_DIR.mkdir(parents=True, exist_ok=True)

DUR      = 60          # целевая длина куска
JITTER   = 5           # ± секунд

def seconds(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=duration", "-of",
         "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True).strip()
    return float(out)

def cut(infile: Path, idx: int):
    total = seconds(infile)
    if total < DUR + 5:
        return  # слишком короткий ролик

    start = random.uniform(5, total - DUR - 5)
    length = DUR + random.uniform(-JITTER, JITTER)

    wav = OUT_DIR / f"voice_{idx}.wav"
    mp3 = OUT_DIR / f"voice_{idx}.mp3"

    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(start), "-t", str(length),
         "-i", str(infile),
         "-ar", "44100", "-ac", "1",
         "-vn", str(wav)],
        check=True)

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav), "-codec:a", "libmp3lame",
         "-qscale:a", "2", str(mp3)],
        check=True)

    wav.unlink()
    print(f"🔊  {mp3.name}  из  {infile.name}")

# --- запускаем ---
for idx, src in enumerate(sorted(IN_DIR.glob("*.mp4")), 1):
    cut(src, idx)
