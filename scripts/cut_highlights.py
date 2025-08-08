#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cut_highlights.py
─────────────────────────────────────────────────────────────────────────────
1.  Скачивает интервью (INTERVIEW_URL) через yt-dlp  
    • сначала пробуем БЕЗ cookies  
    • если YouTube просит авторизацию → пробуем с cookies.txt  
2.  Отдаёт аудио в Whisper (o3 / o4-mini / whisper-1) → JSON-транскрипт  
3.  Делит выпуск на N_SEGMENTS ≈ одинаковой длины  
4.  Каждому сегменту «обрезает» CLIP_SEC ± 1 с, сохраняет в scripts/audio/voice_*.mp3
"""

# ───────────────────────── Настройки ───────────────────────────────────────
INTERVIEW_URL   = "https://www.youtube.com/watch?v=zV7lrWumc7U"    # замените
N_SEGMENTS      = 4          # 4 шорта  →  2 в день × 2 дня
CLIP_SEC        = 30         # длительность фрагмента
LEADING_SEC     = 10         # сдвиг, чтобы не резало слова
MODEL           = "whisper-1"  # или "o4-mini", "gpt-4o-mini"
# ───────────────────────────────────────────────────────────────────────────

import io, os, sys, json, math, shutil, tempfile, textwrap
from pathlib import Path

import yt_dlp, httpx, mutagen
from pydub import AudioSegment
from openai import OpenAI

TMP         = Path(tempfile.gettempdir())
AUDIO_DIR   = Path(__file__).parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# ------------- ключ OpenAI -------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
assert OPENAI_API_KEY, "Нет OPENAI_API_KEY"
client = OpenAI(api_key=OPENAI_API_KEY)

# ------------- подготовка cookies -----------------------------------------
COOKIES_FILE = Path("cookies.txt")          # workflow пишет его перед запуском

def youtube_download(url: str) -> Path:
    """
    Пробуем скачать аудио сперва без cookie; если YouTube просит логин —
    повторяем с cookies.txt. Если и после этого ошибка «Sign in …»
    → завершаем джоб нейтрально (exit 78), чтобы workflow был зелёным.
    """
    def _try(cookiefile: str | None) -> Path | None:
        out = TMP / "full.m4a"
        if out.exists(): out.unlink()
        opts = {
            "quiet":    True,
            "outtmpl":  str(out),
            "format":   "bestaudio[ext=m4a]/bestaudio/best",
            "cookiefile": cookiefile,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return out
        except yt_dlp.utils.DownloadError as e:
            if "Sign in to confirm" in str(e):
                return None
            raise                      # любая другая ошибка → падаем красным

    # 1) без cookies
    m4a = _try(None)
    if m4a: 
        return m4a

    # 2) c cookies.txt
    if COOKIES_FILE.exists():
        m4a = _try(str(COOKIES_FILE))
        if m4a:
            return m4a

    # 3) не удалось — завершаем джоб нейтрально
    print("ℹ️  YouTube требует авторизацию — выпуск пропущен")
    sys.exit(78)                       # neutral в GitHub Actions

def whisper_segments(m4a: Path) -> list[dict]:
    with open(m4a, "rb") as f:
        audio = f.read()
    resp = client.audio.transcriptions.create(
        file=(m4a.name, io.BytesIO(audio)),
        model=MODEL,
        response_format="verbose_json",
    )
    return json.loads(resp.json())["segments"]

def main() -> None:
    m4a      = youtube_download(INTERVIEW_URL)
    segments = whisper_segments(m4a)

    total    = mutagen.File(m4a).info.length
    step     = (total - LEADING_SEC) / N_SEGMENTS
    borders  = [max(0, int(LEADING_SEC + i*step)) for i in range(N_SEGMENTS)]

    audio = AudioSegment.from_file(m4a)
    for idx, start in enumerate(borders, 1):
        clip = audio[start*1000 : (start+CLIP_SEC)*1000]
        path = AUDIO_DIR / f"voice_{idx}.mp3"
        clip.export(path, format="mp3", bitrate="128k")
        print("🔊", path.name)

    print("✅  Готово:", len(borders), "клипов")

if __name__ == "__main__":
    main()
