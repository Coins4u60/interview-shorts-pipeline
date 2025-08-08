#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cut_highlights.py
─────────────────────────────────────────────────────────────────────────────
1. Скачивает интервью (INTERVIEW_URL) через yt-dlр *только если ролик
   отдают без авторизации* (cookies не нужны)
2. Отдаёт аудио в Whisper (gpt-4o-mini или whisper-1) и получает сегменты
3. Делит выпуск на N_SEGMENTS ≈ одинаковой длины
4. Каждому отрезку «обрезает» 30 ± 1 с и кладёт в scripts/audio/voice_*.mp3
"""

# ───────────────────────── Настройки ───────────────────────────────────────
INTERVIEW_URL   = "https://www.youtube.com/watch?v=zV7lrWumc7U"
N_SEGMENTS      = 4          # 4 шорта (по 2 в день)
CLIP_SEC        = 30         # длительность обрезка
LEADING_SEC     = 10         # сдвиг, чтобы не резало слова
MODEL           = "whisper-1"  # или "gpt-4o-mini"
# ───────────────────────────────────────────────────────────────────────────

import io, os, sys, json, math, tempfile, subprocess, textwrap, shutil
from pathlib import Path

import yt_dlp, httpx, mutagen
from pydub import AudioSegment
from openai import OpenAI                        # openai-python ≥ 1.12.0

# каталоги ──────────────────────────────────────────────────────────────────
TMP        = Path(tempfile.gettempdir())
AUDIO_DIR  = Path(__file__).parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --------------------------------------------------------------------------


def download_audio(url: str) -> Path:
    """
    Пытаемся скачать лучший m4a без авторизации.
    Если YouTube требует логин – завершаем job нейтрально (exit-code 78).
    """
    dst = TMP / "full.m4a"
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(dst),
        "quiet":   True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return dst
    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "Sign in to confirm" in msg or "cookies" in msg:
            print("ℹ️ YouTube требует авторизацию – выпуск пропущен")
            sys.exit(78)          # neutral
        raise


def whisper_segments(m4a: Path) -> list[dict]:
    """
    Возвращает список сегментов Whisper (start/end/text).
    """
    with m4a.open("rb") as f:
        res = client.audio.transcriptions.create(
            file=(m4a.name, io.BytesIO(f.read())),
            model=MODEL,
            response_format="verbose_json",
        )
    return res.segments                      # у объекта уже есть .segments


def main() -> None:
    full      = download_audio(INTERVIEW_URL)
    segments  = whisper_segments(full)

    total_sec = mutagen.File(full).info.length
    step      = (total_sec - LEADING_SEC) / N_SEGMENTS
    borders   = [max(0, int(LEADING_SEC + i * step)) for i in range(N_SEGMENTS)]

    audio = AudioSegment.from_file(full)
    for idx, start in enumerate(borders, 1):
        clip = audio[start * 1000 : (start + CLIP_SEC) * 1000]
        out  = AUDIO_DIR / f"voice_{idx}.mp3"
        clip.export(out, format="mp3", bitrate="128k")
        print("🔊", out.name)

    print(f"✅ Сохранено {len(borders)} клипов в {AUDIO_DIR.relative_to(Path.cwd())}")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    main()
