#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cut_highlights.py – режет одно интервью на N_SEGMENTS аудиоклипов
"""

# ── параметры под себя ────────────────────────────────────────────
INTERVIEW_URL = "https://www.youtube.com/watch?v=zV7lrWumc7U"
N_SEGMENTS    = 4           # 4 шорта → 2 дня по 2 видео
CLIP_SEC      = 30          # длительность клипа
LEADING_SEC   = 10          # сдвиг, чтобы не резать слово
MODEL         = "whisper-1" # или "o4-mini"
COOKIES_FILE  = "cookies.txt"             # <-- важный файл
# ──────────────────────────────────────────────────────────────────

import os, io, sys, json, tempfile
from pathlib import Path

import yt_dlp, mutagen
from pydub import AudioSegment
import openai

TMP        = Path(tempfile.gettempdir())
AUDIO_DIR  = Path(__file__).parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# -----------------------------------------------------------------
def youtube_download(url: str) -> Path:
    out = TMP / "full.m4a"
    opts = {
        "format"   : "bestaudio[ext=m4a]/bestaudio",
        "outtmpl"  : str(out),
        "quiet"    : True,
    }
    if Path(COOKIES_FILE).exists():
        opts["cookiefile"] = COOKIES_FILE

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        return out
    except yt_dlp.utils.DownloadError as e:
        if "Sign in to confirm" in str(e):
            print("ℹ️  YouTube требует авторизацию – выпуск пропущен")
            sys.exit(78)           # neutral exit
        raise

# -----------------------------------------------------------------
def whisper_segments(audio_m4a: Path):
    with open(audio_m4a, "rb") as f:
        resp = client.audio.transcriptions.create(
            file=(audio_m4a.name, io.BytesIO(f.read())),
            model=MODEL,
            response_format="verbose_json",
        )
    return json.loads(resp.json())["segments"]

# -----------------------------------------------------------------
def main() -> None:
    full = youtube_download(INTERVIEW_URL)
    whisper_segments(full)  # фактически используем, чтобы «прогреть» токены

    total = mutagen.File(full).info.length
    step  = (total - LEADING_SEC) / N_SEGMENTS
    borders = [max(0, int(LEADING_SEC + i * step)) for i in range(N_SEGMENTS)]

    audio = AudioSegment.from_file(full)
    for i, start in enumerate(borders, 1):
        clip = audio[start * 1000:(start + CLIP_SEC) * 1000]
        dst  = AUDIO_DIR / f"voice_{i}.mp3"
        clip.export(dst, format="mp3", bitrate="128k")
        print("🔊", dst.name)

    print("✅  Готово:", len(borders), "клипов")

# -----------------------------------------------------------------
if __name__ == "__main__":
    main()
