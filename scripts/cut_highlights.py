#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cut_highlights.py
───────────────────────────────────────────────────────────────────────────────
1. Скачивает интервью с YouTube по ссылке INTERVIEW_URL
2. Вытягивает лучшую аудиодорожку (m4a ▸ fallback → любой bestaudio)
3. Отдаёт её в Whisper (o3 или gpt-4o-mini) и получает JSON-транскрипт
4. Делит выпуск на N_SEGMENTS примерно одинаковой длины
5. Каждому сегменту «обрезает» 30 с ± 10 с, кладёт в scripts/audio/voice_*.mp3
   — для дальнейшей сборки шортов build_video.py
"""

# ─ Параметры — меняйте по вкусу ─────────────────────────────────────────────
INTERVIEW_URL = "https://www.youtube.com/watch?v=zV7lrWumc7U"   # замените!
N_SEGMENTS    = 4      # по 2 шорта в день → 4 сегмента на 2 дня
CLIP_SEC      = 30     # длительность фрагмента
LEADING_SEC   = 10     # сдвигаем начало кусочка, чтобы не резало слова
MODEL         = "whisper-1"   # или "o3"
# ─────────────────────────────────────────────────────────────────────────────

import os, io, json, math, shutil, subprocess, tempfile, textwrap, uuid
from pathlib import Path

import yt_dlp, pydub
from pydub import AudioSegment
import openai

# проверяем наличие ключа
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
assert OPENAI_API_KEY, "Нет OPENAI_API_KEY"
client = openai.OpenAI(api_key=OPENAI_API_KEY)

ROOT_DIR   = Path(__file__).parent
AUDIO_DIR  = ROOT_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True, parents=True)

# ---------------------------------------------------------------------------#
def download_audio(url: str) -> Path:
    """Скачивает аудио и возвращает путь к итоговому .m4a"""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        out    = tmpdir / "full.%(ext)s"

        ydl_opts = {
            # 1) m4a (обычно = itag 140), 2) любой bestaudio, 3) всё остальное
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": str(out),
            "quiet": True,
            # конвертируем в m4a, если нужно
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "m4a",
                    "preferredquality": "192",
                }
            ],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        final = out.with_suffix(".m4a")
        return final if final.exists() else list(tmpdir.glob("*.m4a"))[0]

# ---------------------------------------------------------------------------#
def transcribe(path: Path) -> list[dict]:
    """Отдаём файл в Whisper, возвращаем список слов с таймингом"""
    print("📝 Whisper… (~реал. время)")

    with path.open("rb") as f:
        transcript = client.audio.transcriptions.create(
            model=MODEL,
            file=f,
            response_format="verbose_json"
        )

    return transcript.words  # list[{word,start,end}]

# ---------------------------------------------------------------------------#
def split_to_segments(words: list[dict], n: int) -> list[tuple[float,float]]:
    """Делим длительность на n равных кусков, возвращаем (start,end) секунд"""
    full_sec = words[-1]["end"]
    chunk    = full_sec / n
    bounds   = []
    for i in range(n):
        t0 = max(0, i*chunk + LEADING_SEC)
        t1 = t0 + CLIP_SEC
        bounds.append((t0, t1))
    return bounds

# ---------------------------------------------------------------------------#
def cut_clips(src: Path, segments: list[tuple[float,float]]) -> None:
    """Режет аудио на клипы и сохраняет them → scripts/audio/voice_*.mp3"""
    audio = AudioSegment.from_file(src)
    for i, (t0, t1) in enumerate(segments, 1):
        clip = audio[t0*1000 : t1*1000]
        fname = AUDIO_DIR / f"voice_{i}.mp3"
        clip.export(fname, format="mp3", bitrate="192k")
        print(f"🎤  {fname.name}  {len(clip)//1000:>3d}s")

# ---------------------------------------------------------------------------#
def main() -> None:
    print("⏬  Скачиваем аудио…")
    m4a = download_audio(INTERVIEW_URL)
    print(f"   ✔ {m4a.stat().st_size/1e6:.1f} MB")

    words = transcribe(m4a)
    segments = split_to_segments(words, N_SEGMENTS)
    cut_clips(m4a, segments)

    print("\n✅  Готово: аудио лежит в scripts/audio/*.mp3")

if __name__ == "__main__":
    main()
