#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Загружает ≤2 новых *.mp4 из scripts/videos/ как Shorts.
"""

import os, pathlib, time, sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http      import MediaFileUpload
from googleapiclient.errors    import HttpError
import google.auth.transport.requests as tr

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
MAX_UPLOADS_PER_RUN = 2          # 2 ролика за запуск

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

HASHTAGS = "#финансы #деньги #инвестиции #личныефинансы #shorts"
TAGS = ["финансы","деньги","финансовая грамотность","инвестиции",
        "money","finance","budget","shorts"]

VIDEOS = sorted((pathlib.Path(__file__).parent / "videos").glob("voice_*.mp4"))
if not VIDEOS:
    sys.exit("❌ Нет mp4 в scripts/videos")

for vid in VIDEOS[:MAX_UPLOADS_PER_RUN]:
    idx = vid.stem.split('_')[-1]
    body = {
        "snippet": {
            "title": f"Short #{idx} • Личный бюджет за 1 минуту",
            "description": "Советы по управлению деньгами\n\n" + HASHTAGS,
            "categoryId": "22",
            "tags": TAGS
        },
        "status": {"privacyStatus": "public"}
    }
    media = MediaFileUpload(vid, mimetype="video/mp4", resumable=True)
    try:
        resp = yt.videos().insert(part="snippet,status",
                                  body=body, media_body=media).execute()
        print(f"📤 https://youtu.be/{resp['id']}  ← {vid.name}")
    except HttpError as e:
        print("❌ Upload error:", e, file=sys.stderr)
        time.sleep(20)
