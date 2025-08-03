#!/usr/bin/env python3
"""
Скачивает интервью, делает транскрипцию Whisper-ом и
вырезает 4 фрагмента ≤45 с → audio/voice_1-4.mp3
"""

import os, math, tempfile, pathlib, shutil, random, time
from typing import List, Tuple
import yt_dlp
from pydub import AudioSegment
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
assert OPENAI_API_KEY, "Нет OPENAI_API_KEY"

URL        = "https://www.youtube.com/watch?v=zV7lrWumc7U"
N_CLIPS    = 4
TARGET_SEC = 45

WORK       = pathlib.Path(__file__).parent
AUDIO_DIR  = WORK / "audio"
shutil.rmtree(AUDIO_DIR, ignore_errors=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(api_key=OPENAI_API_KEY)

# ───────────────────────── helpers ──────────────────────────
def download_audio(url: str) -> pathlib.Path:
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".m4a").name
    with yt_dlp.YoutubeDL({"format": "bestaudio[m4a]", "outtmpl": out,
                           "quiet": True, "noprogress": True}) as ydl:
        ydl.download([url])
    return pathlib.Path(out)

def whisper_segments(path: pathlib.Path) -> List[Tuple[float,str]]:
    with open(path, "rb") as f:
        res = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )
    return [(s["start"], s["text"].strip()) for s in res.segments]  # type: ignore

def group_segments(segs, n=N_CLIPS, limit=TARGET_SEC):
    clips, buf, buf_t, start = [], [], 0.0, 0.0
    for t, txt in segs:
        if buf and t - start > limit:
            clips.append((start, buf_t, " ".join(buf)))
            buf, buf_t = [], 0.0
        if not buf:
            start = t
        buf.append(txt)
        buf_t = t - start + 5
        if len(clips) == n:
            break
    if buf and len(clips) < n:
        clips.append((start, buf_t, " ".join(buf)))
    return clips[:n]

def export(src: pathlib.Path, num: int, start: float, length: float):
    dst = AUDIO_DIR / f"voice_{num}.mp3"
    (
        AudioSegment.from_file(src)
        .set_channels(1)[start*1000:(start+length)*1000]
        .export(dst, format="mp3", bitrate="128k")
    )

# ───────────────────────── main ─────────────────────────────
def main():
    m4a = download_audio(URL)
    print("✅ скачано", m4a)
    segs = whisper_segments(m4a)
    clips = group_segments(segs)
    for i, (st, ln, txt) in enumerate(clips, 1):
        export(m4a, i, st, ln)
        print(f"🎤 voice_{i}.mp3  {ln:.1f}s  {txt[:60]}…")
    pathlib.Path(m4a).unlink(missing_ok=True)

if __name__ == "__main__":
    main()
