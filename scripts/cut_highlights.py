#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1) скачивает интервью (audio-only m4a, fallback bestaudio)
2) распознаёт Whisper-v3 (через openai-python)
3) режет на N_SEGMENTS примерно одинаковой длины
4) обрезает +10 s спереди, +CLIP_SEC сзади
5) кладёт voice_*.mp3 в scripts/audio/   (для build_video.py)
"""

import os, json, math, shutil, subprocess, tempfile, textwrap, io, sys, re, time
from pathlib import Path
import yt_dlp, httpx
from pydub import AudioSegment
import openai

# ───────────────── настройки ─────────────────
INTERVIEW_URL = "https://www.youtube.com/watch?v=zV7lrWumc7U"
N_SEGMENTS    = 4          # 2 шорта в день × 2 дня
CLIP_SEC      = 30         # длина шорта
LEADING_SEC   = 10         # оставляем небольшой «разгон»
MODEL         = "whisper-1"
# ─────────────────────────────────────────────

ROOT = Path(__file__).parent
AUDIO_DIR = ROOT / "audio"
AUDIO_DIR.mkdir(exist_ok=True)
TMP = tempfile.TemporaryDirectory(prefix="yt_")
@@
 def download_audio(url: str) -> Path:
+    # DEBUG: убедимся, что куки действительно есть
+    ck = os.environ.get("YT_COOKIES")
+    print("▶️  YT_COOKIES length:", len(ck or "0"))
+
     with tempfile.NamedTemporaryFile("w+", suffix=".txt") as f:
         f.write(os.environ["YT_COOKIES"])
         f.flush()

def download_audio(url: str) -> Path:
    """Скачиваем m4a (или лучшее аудио) в TMP и возвращаем путь."""
    out = str(Path(TMP.name) / "%(id)s.%(ext)s")

    ytdl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio",
        "outtmpl": out,
        "quiet": True,
        "overwrite": True,
    }

    cookies_txt = os.getenv("YT_COOKIES", "").strip()
    if cookies_txt:
        cfile = Path(TMP.name) / "cookies.txt"
        cfile.write_text(cookies_txt, encoding="utf-8")
        ytdl_opts["cookiefile"] = str(cfile)

    with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
        info = ydl.extract_info(url)
        return Path(ydl.prepare_filename(info))

def whisper_transcribe(wav: Path) -> list[str]:
    """Отдаём на Whisper v3 и возвращаем JSON list [{start,end,text},…]."""
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    with wav.open("rb") as f:
        resp = client.audio.transcriptions.create(
            model=MODEL, file=f, response_format="verbose_json"
        )
    return resp.segments  # type: ignore

def main() -> None:
    m4a = download_audio(INTERVIEW_URL)
    wav = m4a.with_suffix(".wav")
    subprocess.run(["ffmpeg", "-y", "-i", m4a, wav], check=True)

    segments = whisper_transcribe(wav)

    total_dur = segments[-1]["end"]
    chunk = total_dur / N_SEGMENTS

    groups: list[list[dict]] = [[] for _ in range(N_SEGMENTS)]
    for seg in segments:
        idx = min(int(seg["start"] // chunk), N_SEGMENTS - 1)
        groups[idx].append(seg)

    for i, segs in enumerate(groups, 1):
        if not segs:
            continue
        start = max(0, segs[0]["start"] - LEADING_SEC)
        end   = start + CLIP_SEC
        out_mp3 = AUDIO_DIR / f"voice_{i}.mp3"

        subprocess.run([
            "ffmpeg", "-y", "-ss", str(start), "-t", str(CLIP_SEC),
            "-i", m4a, "-vn", "-acodec", "libmp3lame", str(out_mp3)
        ], check=True)

        text = " ".join(s["text"].strip() for s in segs)
        print(f"TTS {i}/{N_SEGMENTS}: {text[:60]}…")

if __name__ == "__main__":
    main()
