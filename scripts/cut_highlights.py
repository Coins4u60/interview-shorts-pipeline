#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cut_highlights.py   – режет интервью на N_SEGMENTS аудиофрагментов
"""

# ── Параметры ───────────────────────────────────────────────────────────
INTERVIEW_URL  = "https://www.youtube.com/watch?v=zV7lrWumc7U"
N_SEGMENTS     = 4          # 2 шорта в день × 2 дня
CLIP_SEC       = 30         # длительность клипа
LEADING_SEC    = 10         # чтобы не резать слово
MODEL          = "whisper-1"
COOKIES_FILE   = "cookies.txt"          # ← важно!
# ────────────────────────────────────────────────────────────────────────

import os, io, sys, json, math, shutil, tempfile, textwrap
from pathlib import Path
import yt_dlp, mutagen, httpx
from pydub import AudioSegment
import openai

TMP = Path(tempfile.gettempdir())
AUDIO_DIR = Path(__file__).parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# -----------------------------------------------------------------------
def youtube_download(url: str) -> Path:
    """
    Пытаемся скачать аудио:
      • если `cookies.txt` найден → скачиваем с куками
      • если без куков YouTube просит логин → нейтрально выходим
    """
    out = TMP / "full.m4a"

    common = {
        "format": "bestaudio[ext=m4a]/bestaudio",
        "outtmpl": str(out),
        "quiet": True,
    }

    opts = common | ({"cookiefile": COOKIES_FILE}
                     if Path(COOKIES_FILE).exists() else {})

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        return out
    except yt_dlp.utils.DownloadError as e:
        if "Sign in to confirm" in str(e):
            print("ℹ️  YouTube требует авторизацию – выпуск пропущен")
            sys.exit(78)        # neutral
        raise

# -----------------------------------------------------------------------
def whisper_segments(m4a: Path) -> list[dict]:
    with open(m4a, "rb") as f:
        resp = client.audio.transcriptions.create(
            file=(m4a.name, io.BytesIO(f.read())),
            model=MODEL,
            response_format="verbose_json",
        )
    return json.loads(resp.json())["segments"]

# -----------------------------------------------------------------------
def main() -> None:
    full = youtube_download(INTERVIEW_URL)
    segs = whisper_segments(full)

    tot = mutagen.File(full).info.length
    step = (tot - LEADING_SEC) / N_SEGMENTS
    borders = [max(0, int(LEADING_SEC + i*step)) for i in range(N_SEGMENTS)]

    audio = AudioSegment.from_file(full)
    for i, start in enumerate(borders, 1):
        clip = audio[start*1000:(start+CLIP_SEC)*1000]
        dst  = AUDIO_DIR / f"voice_{i}.mp3"
        clip.export(dst, format="mp3", bitrate="128k")
        print("🔊", dst.name)

    print("✅  Готово:", len(borders), "клипов")

# -----------------------------------------------------------------------
if __name__ == "__main__":
    main()
