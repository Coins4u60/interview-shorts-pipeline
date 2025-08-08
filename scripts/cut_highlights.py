#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cut_highlights.py
─────────────────────────────────────────────────────────────────────────────
1.  Скачивает интервью (INTERVIEW_URL) через yt-dlp без авторизации
2.  Отдаёт аудио в Whisper (oz или o4-mini) и получает JSON-транскрипт
3.  Делит выпуск на N_SEGMENTS ≈ одинаковой длины
4.  Каждому сегменту «обрезает» 30 ± 1 с аудио ⇢ scripts/audio/voice_*.mp3
"""

# ───────────────────────── Настройки ───────────────────────────────────────
INTERVIEW_URL   = "https://www.youtube.com/watch?v=zV7lrWumc7U"   # поменяйте
N_SEGMENTS      = 4        # 4 шорта → 2 в день
CLIP_SEC        = 30       # длительность фрагмента
LEADING_SEC     = 10       # сдвиг, чтобы не резало слова
MODEL           = "whisper-1"  # или "o4-mini"
# ───────────────────────────────────────────────────────────────────────────

import os, io, sys, json, math, shutil, subprocess, tempfile, textwrap
from pathlib import Path
import yt_dlp, httpx, mutagen
from pydub import AudioSegment
import openai

TMP = Path(tempfile.gettempdir())
AUDIO_DIR = Path(__file__).parent / "audio"
AUDIO_DIR.mkdir(exist_ok=True, parents=True)

openai_client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# ---------------------------------------------------------------------------
def download_audio(url: str) -> Path:
    """
    Скачиваем аудио только _если_ YouTube отдает ролик без авторизации.
    Если видим ошибку «Sign-in to confirm you’re not a bot» → пропускаем выпуск.
    """
    out = TMP / "full.m4a"
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(out),
        "quiet": True,
        # ! главное – НЕ передаём cookies и не пытаемся логиниться
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return out
    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "Sign in to confirm" in msg or "cookies" in msg:
            # YouTube не дал скачать без логина – завершаем джоб нейтрально
            print("ℹ️  YouTube требует авторизацию – выпуск пропущен")
            sys.exit(78)         # 78 = GitHub Actions «neutral»
        raise                    # любая другая ошибка – падаем красным

# ---------------------------------------------------------------------------
def whisper_json(m4a: Path) -> list[dict]:
    with open(m4a, "rb") as f:
        audio = f.read()
    resp = openai_client.audio.transcriptions.create(
        file=(m4a.name, io.BytesIO(audio)),
        model=MODEL,
        response_format="verbose_json",
    )
    return json.loads(resp.json())["segments"]

# ---------------------------------------------------------------------------
def main():
    full      = download_audio(INTERVIEW_URL)
    segments  = whisper_json(full)

    # Вычисляем границы, чтобы получилось N_SEGMENTS клипов ≈ CLIP_SEC
    total_sec = mutagen.File(full).info.length
    step      = (total_sec - LEADING_SEC) / N_SEGMENTS
    borders   = [max(0, int(LEADING_SEC + i*step)) for i in range(N_SEGMENTS)]

    audio = AudioSegment.from_file(full)
    for idx, start in enumerate(borders, 1):
        clip = audio[start*1000 : (start+CLIP_SEC)*1000]
        path = AUDIO_DIR / f"voice_{idx}.mp3"
        clip.export(path, format="mp3", bitrate="128k")
        print("🔊", path.name)

    print("✅  Готово:", len(borders), "клипов")

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
