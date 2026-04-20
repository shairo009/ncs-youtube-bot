import json
import os
import random
import sys
import requests
from chess_voice import generate_voice
from chess_editor import create_video
from uploader import run_upload  # ncs-youtube-bot ka existing uploader

with open("chess_prompt.txt") as f:
    PROMPT_TEMPLATE = f.read()

TONES = ["Shock 😱", "Funny 😂", "Savage 😈", "Smart 😎"]

OPENROUTER_API_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
ELEVENLABS_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")

TOP_PLAYERS = [
    "DrNykterstein", "nihalsarin", "DanielNaroditsky",
    "penguingim1", "alireza2003", "LyonBeast",
    "Zhigalko_Sergei", "rpragchess", "vincentkeymer",
    "Firouzja2003", "mishanick", "Baskaran_Adhiban",
]


def fetch_game():
    player = random.choice(TOP_PLAYERS)
    print(f"Fetching game from: {player}")
    url = f"https://lichess.org/api/games/user/{player}?max=30&analysed=true&evals=true&perfType=bullet,blitz"
    r = requests.get(url, headers={"Accept": "application/x-ndjson"}, stream=True, timeout=20)
    games = []
    for line in r.iter_lines():
        if line:
            try:
                games.append(json.loads(line))
            except Exception:
                pass
    if not games:
        raise Exception(f"No games found for {player}")
    return random.choice(games), player


def extract_blunder(game):
    analysis = game.get("analysis", [])
    blunders = [(i, m) for i, m in enumerate(analysis)
                if m.get("judgment", {}).get("name") in ["Blunder", "Mistake"]]
    if not blunders:
        return None
    idx, move = random.choice(blunders)
    return {"game_id": game.get("id", "unknown"), "blunder_index": idx}


def call_openrouter(tone, player):
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/shairo009/ncs-youtube-bot",
            "X-Title": "Chess Bot YT"
        },
        json={
            "model": "mistralai/mistral-7b-instruct:free",
            "messages": [
                {"role": "system", "content": "You are a Hinglish YouTube Shorts chess creator. Use exact OUTPUT format only."},
                {"role": "user", "content": PROMPT_TEMPLATE + f"\n\nTone: {tone}\nPlayer: {player}"}
            ],
            "temperature": 0.9,
            "max_tokens": 500
        },
        timeout=30
    )
    if r.status_code != 200:
        raise Exception(f"OpenRouter error: {r.status_code}")
    return r.json()["choices"][0]["message"]["content"]


def parse_script(raw):
    result = {}
    current = None
    for line in raw.strip().split("\n"):
        for key in ["HOOK", "VOICE_LINES", "STYLE", "TITLE", "DESCRIPTION", "HASHTAGS", "EDIT_PLAN"]:
            if line.startswith(f"{key}:"):
                current = key
                result[key] = line[len(key)+1:].strip()
                break
        else:
            if current and line.strip():
                result[current] = result.get(current, "") + "\n" + line.strip()
    return result


def run():
    os.makedirs("downloads", exist_ok=True)
    tone = random.choice(TONES)
    print(f"Tone: {tone}")

    game, player = fetch_game()
    blunder = extract_blunder(game)
    if not blunder:
        raise Exception("No blunder found, retrying next run")

    print(f"Game: {blunder['game_id']} | Blunder: move {blunder['blunder_index']}")

    raw = call_openrouter(tone, player)
    script = parse_script(raw)
    print("Script:", json.dumps(script, indent=2, ensure_ascii=False))

    voice_file = generate_voice(
        text=script.get("HOOK", "") + " " + script.get("VOICE_LINES", ""),
        output_path="downloads/chess_voice.mp3",
        voice_id=ELEVENLABS_VOICE_ID,
        api_key=ELEVENLABS_API_KEY
    )

    video_file = create_video(
        game_id=blunder["game_id"],
        blunder_index=blunder["blunder_index"],
        voice_file=voice_file,
        output_path="downloads/final_video.mp4"
    )

    title = script.get("TITLE", "Chess Blunder 😱 #Shorts")
    desc = script.get("DESCRIPTION", "") + "\n\n" + script.get("HASHTAGS", "")

    # ncs-youtube-bot ka uploader use kar raha hai
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.http import MediaFileUpload
    import googleapiclient.errors

    creds = Credentials.from_authorized_user_file("token.json",
        ["https://www.googleapis.com/auth/youtube.upload"])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": desc,
            "tags": ["chess", "chessblunder", "chesshindi", "shorts"],
            "categoryId": "20"
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    req = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
    )
    response = req.execute()
    print(f"✅ Uploaded! https://youtu.be/{response['id']}")


if __name__ == "__main__":
    run()
