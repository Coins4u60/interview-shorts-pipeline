#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cut_highlights.py
────────────────────────────────────────────────────────────
1. Скачивает интервью с YouTube по ссылке INTERVIEW_URL
2. Вытягивает лучший аудиопоток (m4a → fallback — любой bestaudio)
3. Отдаёт в Whisper (o3 или gpt-4o-mini) и получает JSON-транскрипт
4. Делит выпуск на N_SEGMENTS примерно одинаковой длины
5. Каждому сегменту «обрезает» 30 с ± 10 с, кладёт в scripts/audio/voice_*.mp3
   ─ для дальнейшей сборки шортов build_video.py
"""

# ─────────────────── Параметры — меняйте по вкусу ──────────────────
INTERVIEW_URL = "https://www.youtube.com/watch?v=zV7lrWumc7U"
              # замените на нужное интервью

N_SEGMENTS    = 4        # «по 2 шорта в день» ⇒ 4 сегмента на 2 дня
CLIP_SEC      = 30       # длительность фрагмента
LEADING_SEC   = 10       # сдвигаем начало кусочка, чтобы не резало слова
MODEL         = "whisper-1"      # или "o3"
# ─────────────────────────────────────────────────────────────────────

import os, io, json, math, shutil, subprocess, tempfile, textwrap
from pathlib import Path
import yt_dlp, pydub
from pydub import AudioSegment
import openai

AUDIO_DIR = Path(__file__).parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR   = tempfile.TemporaryDirectory()

openai.api_key = os.environ["OPENAI_API_KEY"]   #  <- даст Assert, если нет
assert openai.api_key, "Нет OPENAI_API_KEY"

# ─ 1. Скачиваем аудио с YouTube ─────────────────────────────────────
print("⏬ Скачиваю аудио…")
audio_path = Path(TMP_DIR.name) / "full.m4a"

YDL_OPTS = {
    "format":       "bestaudio[ext=m4a]/bestaudio",
    "outtmpl":      str(audio_path),
    "quiet":        True,
    "no_warnings":  True,
}
with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
    ydl.download([INTERVIEW_URL])

# Если попался webm/opus — конвертируем в m4a (Whisper примет любой, но m4a проще)
if audio_path.suffix != ".m4a":
    src = audio_path
    audio_path = audio_path.with_suffix(".m4a")
    subprocess.run(["ffmpeg", "-y", "-i", str(src), str(audio_path)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print(f"✅ Аудио: {audio_path.name} {audio_path.stat().st_size/1e6:.1f} MB")

# ─ 2. Отправляем в Whisper и получаем сегменты ─────────────────────
print("📝 Расшифровка Whisper… (может занять несколько минут)")
with audio_path.open("rb") as f:
    resp = openai.audio.transcriptions.create(
        model=MODEL,
        file=f,
        response_format="verbose_json",
        timestamp_granularities=["segment"],
        language="ru"          # понадобится, если интервью русское
    )
segments = resp.segments
duration = resp.duration   # float, сек

print(f"   Интервью длится {duration/60:.1f} мин, всего сегментов Whisper: {len(segments)}")

# ─ 3. Выбираем N_SEGMENTS точек равноотстоящих по времени ──────────
step = duration / N_SEGMENTS
targets = [step/2 + i*step for i in range(N_SEGMENTS)]   # t≈ ¼, ¾ …

def nearest_segment(time_sec: float):
    return min(segments, key=lambda s: abs(s["start"] - time_sec))

highlights = []
for t in targets:
    seg = nearest_segment(t)
    clip_start = max(0, seg["start"] - LEADING_SEC)
    highlights.append((clip_start, clip_start + CLIP_SEC))

# ─ 4. Нарезаем MP3 файлы ────────────────────────────────────────────
sound = AudioSegment.from_file(audio_path)

for i, (start, end) in enumerate(highlights, 1):
    clip = sound[start*1000 : end*1000]      # pydub — миллисекунды
    out = AUDIO_DIR / f"voice_{i}.mp3"
    clip.export(out, format="mp3", bitrate="192k")
    print(f"🎧 voice_{i}.mp3  [{start:>6.1f} – {end:>6.1f} с]")

print("\n✅  Готово. Аудио-кусочки лежат в  scripts/audio/ .")
TMP_DIR.cleanup()
