#!/usr/bin/env python3
"""
Заливает все mp4 из videos/ как PUBLIC-Shorts.
"""

import os, pathlib, sys, time
from googleapiclient.discovery import build
from googleapiclient.http      import MediaFileUpload
from googleapiclient.errors    import HttpError
from google.oauth2.credentials import Credentials
import google.auth.transport.requests as tr

YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

creds = Credentials(
    None,
    refresh_token = os.getenv("YT_REFRESH_TOKEN"),
    client_id     = os.getenv("YT_CLIENT_ID"),
    client_secret = os.getenv("YT_CLIENT_SECRET"),
    token_uri     = "https://oauth2.googleapis.com/token",
    scopes        = YT_SCOPES,
)
creds.refresh(tr.Request())
yt = build("youtube", "v3", credentials=creds, cache_discovery=False)

TAGLIST = ["финансы","личные финансы","деньги","shorts","money","finance"]

VIDEOS = sorted(pathlib.Path("videos").glob("voice_*.mp4"))
if not VIDEOS:
    sys.exit("❌  Нет mp4 в videos/")

for vid in VIDEOS:
    idx = vid.stem.split('_')[-1]
    body = {
        "snippet": {
            "title": f"Финсовет #{idx} • до 1 минуты",
            "description": "Короткие советы по управлению деньгами #финансы #shorts",
            "categoryId": "22",
            "tags": TAGLIST,
        },
        "status": {"privacyStatus": "public"}
    }
    media = MediaFileUpload(vid, mimetype="video/mp4", resumable=True)
    try:
        resp = yt.videos().insert(part="snippet,status", body=body,
                                  media_body=media).execute()
        print("📤", f"https://youtu.be/{resp['id']}")
    except HttpError as e:
        if e.resp.status == 403 and "uploadLimitExceeded" in e.error_details[0]["reason"]:
            sys.exit("⚠️  Дневной лимит YouTube исчерпан")
        print("❌  Ошибка загрузки:", e)
        time.sleep(15)
