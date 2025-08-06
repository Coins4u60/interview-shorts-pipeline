#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Загружает все *.mp4 из scripts/videos/ как Shorts
(privacyStatus = public).
"""

import os, pathlib, time, sys
import google.auth.transport.requests as tr
from googleapiclient.discovery import build
from googleapiclient.http      import MediaFileUpload
from googleapiclient.errors    import HttpError
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
HASHTAGS = "#финансы #инвестиции #shorts #money #finance"

creds = Credentials(
    None,
    refresh_token = os.environ["YT_REFRESH_TOKEN"],
    client_id     = os.environ["YT_CLIENT_ID"],
    client_secret = os.environ["YT_CLIENT_SECRET"],
    token_uri     = "https://oauth2.googleapis.com/token",
    scopes        = SCOPES,
)
creds.refresh(tr.Request())
yt = build("youtube", "v3", credentials=creds, cache_discovery=False)

VIDEOS = sorted((pathlib.Path(__file__).parent / "videos").glob("voice_*.mp4"))
if not VIDEOS:
    sys.exit("Нет mp4 для загрузки")

for vid in VIDEOS:
    idx = vid.stem.split('_')[-1]
    body = {
        "snippet": {
            "title": f"Short #{idx} • Лучшие мысли из интервью",
            "description": f"Короткий фрагмент интервью.\n\n{HASHTAGS}",
            "categoryId": "22",
            "tags": ["финансы","инвестиции","личные финансы","shorts","money","finance"],
        },
        "status": {"privacyStatus": "public"}
    }
    try:
        req = yt.videos().insert(
            part="snippet,status",
            body=body,
            media_body=MediaFileUpload(vid, mimetype="video/mp4", resumable=True)
        )
        resp = req.execute()
        print("📤", f"https://youtu.be/{resp['id']}")
    except HttpError as e:
        print("Upload error:", e)
        time.sleep(20)
