#!/usr/bin/env python3
"""
Вырезает 2 фрагмента (35-45 с) из input/interview.mp4
* Детектируем тишину ➜ берём самые «шумные» куски
* Расшифровываем Whisper-ом ➜ subtitles в scripts/lines.txt
* Экспортируем mp3 в scripts/audio/voice_1.mp3, voice_2.mp3
"""

from pathlib import Path
import random, subprocess, tempfile, json, sys
from pydub import AudioSegment, silence
import whisper_timestamped as whisper

SRC = Path("input/interview.mp4")
if not SRC.exists():
    sys.exit("❌  Положите исходное интервью в input/interview.mp4")

WORK = Path("scripts/audio")
WORK.mkdir(parents=True, exist_ok=True)

# ─ 1. mp4 → wav ─────────────────────────────────────────────────────
wav = WORK / "tmp.wav"
subprocess.run(["ffmpeg", "-y", "-i", SRC, "-ac", "1", "-ar", "16000", wav])

sound = AudioSegment.from_wav(wav)
chunks = silence.detect_nonsilent(sound, min_silence_len=700, silence_thresh=-40)

# выбираем 2 случайных куска по 35-45 с
parts = []
for _ in range(2):
    beg, end = random.choice(chunks)
    while end - beg < 35_000 or end - beg > 45_000:
        beg, end = random.choice(chunks)
    parts.append(sound[beg:end])

# ─ 2. сохраняем mp3 + ASR ───────────────────────────────────────────
lines = []
for i, seg in enumerate(parts, 1):
    mp3 = WORK / f"voice_{i}.mp3"
    seg.export(mp3, format="mp3", bitrate="192k")

    # Whisper-ASR
    result = whisper.transcribe("small", mp3, language="ru", vad="silero")
    text = " ".join([w["text"] for w in result["segments"]]).strip()
    lines.append(text)

Path("scripts/lines.txt").write_text("\n".join(lines), "utf-8")
print("✅  audio/voice_*.mp3 + lines.txt готово")
