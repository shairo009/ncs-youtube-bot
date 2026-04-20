import subprocess
import random
import os
import re
import json
import time
from urllib.parse import quote_plus

HISTORY_FILE   = "downloads_history.txt"
COOKIES_FILE   = "cookies.txt"
NCS_SOUNDCLOUD = "https://soundcloud.com/nocopyrightsounds"
NCS_YOUTUBE    = "https://www.youtube.com/@NoCopyrightSounds/videos"
TOR_PROXY      = "socks5://127.0.0.1:9050"

HUMAN_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]

# Updated working Cobalt instances (co.wuk.sh DEAD — removed)
COBALT_INSTANCES = [
    "https://api.cobalt.tools/",
    "https://cobalt.api.timelessnesses.me/",
    "https://cobalt.catto.space/",
]

# Invidious public instances (YouTube proxy — no bot detection)
INVIDIOUS_INSTANCES = [
    "https://invidious.snopyta.org",
    "https://yt.artemislena.eu",
    "https://invidious.nerdvpn.de",
    "https://inv.tux.pizza",
    "https://invidious.privacyredirect.com",
    "https://vid.priv.au",
]


# ── History helpers ──────────────────────────────────────
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()


def save_to_history(track_id):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(str(track_id) + "\n")


def detect_genre(title):
    genre = "NCS Release"
    title_clean = title.replace("｜", "|")
    if "|" in title_clean:
        parts = [p.strip() for p in title_clean.split("|")]
        if len(parts) >= 2 and parts[1]:
            genre = parts[1]
    return genre


def is_generic_genre(genre):
    return not genre or genre.strip().lower() in {"ncs release", "ncs", "copyright free music", "release"}


def _normalize_track_text(value):
    value = (value or "").lower().replace("｜", "|")
    value = value.split("|")[0]
    value = re.sub(r"\[[^\]]*(ncs|release|copyright|free|music)[^\]]*\]", " ", value, flags=re.I)
    value = re.sub(r"\([^)]*(version|edit|mix|remix|visualizer|lyrics|tiktok|sped|slowed)[^)]*\)", " ", value, flags=re.I)
    value = re.sub(r"\b(ncs|no copyright sounds|copyright free music|official|video|visualizer)\b", " ", value, flags=re.I)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def infer_genre_from_ncs_tracks(title, tracks):
    target = _normalize_track_text(title)
    if not target:
        return "NCS Release"

    best = None
    best_score = 0
    target_words = set(target.split())
    for track in tracks or []:
        candidate = _normalize_track_text(track.get("title", ""))
        genre = track.get("genre") or "NCS Release"
        if not candidate or is_generic_genre(genre):
            continue
        candidate_words = set(candidate.split())
        score = len(target_words & candidate_words)
        if target == candidate or target in candidate or candidate in target:
            score += 10
        if score > best_score:
            best_score = score
            best = genre

    if best and best_score >= 2:
        print(f"  Genre match: '{title}' → {best}")
        return best
    return "NCS Release"


def _ncs_search_queries(title):
    cleaned = (title or "").replace("｜", "|").split("|")[0]
    cleaned = re.sub(r"\[[^\]]*\]", " ", cleaned)
    cleaned = re.sub(r"\([^)]*(version|edit|mix|remix|visualizer|lyrics|tiktok|sped|slowed)[^)]*\)", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    queries = []
    if " - " in cleaned:
        artist, track = cleaned.split(" - ", 1)
        queries.extend([track.strip(), artist.strip(), cleaned])
    else:
        queries.append(cleaned)

    normalized = _normalize_track_text(cleaned)
    words = [w for w in normalized.split() if len(w) > 2]
    if words:
        queries.append(" ".join(words[:4]))
        queries.extend(words[:3])

    unique = []
    seen = set()
    for query in queries:
        query = query.strip(" -,.![]()")
        key = query.lower()
        if query and key not in seen:
            seen.add(key)
            unique.append(query)
    return unique


def lookup_genre_from_ncs_io(title):
    for query in _ncs_search_queries(title):
        tracks = fetch_tracks_from_ncs_io(search_query=query)
        genre = infer_genre_from_ncs_tracks(title, tracks)
        if not is_generic_genre(genre):
            return genre
    return "NCS Release"


def _cleanup_temp(path):
    """Remove leftover temp file so next engine starts clean."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────
# ENGINE 1: NCS.io — direct CDN download + SoundCloud fallback
#   Fix: proper session headers + Referer + CDN direct URL
#   Fix: import re was missing before
# ─────────────────────────────────────────────────────────
def fetch_tracks_from_ncs_io(search_query=""):
    try:
        import requests
        from bs4 import BeautifulSoup

        print("Engine 1: Fetching tracks from NCS.io...")
        session = requests.Session()
        session.headers.update({
            "User-Agent": random.choice(HUMAN_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://ncs.io/",
        })
        # Warm-up visit to get session cookies (avoids bot block)
        session.get("https://ncs.io/", timeout=20)
        time.sleep(random.uniform(1.0, 2.5))

        if search_query:
            offset = 0
            url = f"https://ncs.io/music-search?q={quote_plus(search_query)}&genre=&mood=&version=&offset=0"
        else:
            offset = random.choice([0, 15, 30, 45, 60, 75, 90, 105, 120])
            url = f"https://ncs.io/music-search?q=&genre=&mood=&version=&offset={offset}"
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        tracks = []
        seen_ids = set()
        for item in soup.find_all(attrs={"data-tid": True}):
            track_id = item.get("data-tid", "").strip()
            if not track_id or track_id in seen_ids:
                continue
            seen_ids.add(track_id)
            artist = item.get("data-artistraw", "").strip()
            track  = item.get("data-track", "").strip()
            genre  = item.get("data-genre", "").strip() or "NCS Release"
            if artist and track:
                tracks.append({"id": track_id, "title": f"{artist} - {track}", "genre": genre})
            elif track:
                tracks.append({"id": track_id, "title": track, "genre": genre})

        print(f"  NCS.io: Found {len(tracks)} tracks at offset {offset}")
        return tracks
    except Exception as e:
        print(f"  NCS.io fetch error: {e}")
        return []


def download_from_ncs_io(track_id, title, output_file):
    """Try NCS.io direct CDN first, then SoundCloud search as fallback."""
    import requests

    # ── Try 1: NCS.io direct CDN download ──
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": random.choice(HUMAN_USER_AGENTS),
            "Referer": "https://ncs.io/music",
            "Accept": "audio/mpeg, audio/*, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })
        session.get("https://ncs.io/", timeout=15)
        time.sleep(random.uniform(0.8, 2.0))

        dl_url = f"https://ncs.io/track/download?tid={track_id}"
        print(f"  Engine 1: Direct CDN download for '{title}'...")
        resp = session.get(dl_url, timeout=120, stream=True, allow_redirects=True)
        if resp.status_code == 200 and "audio" in resp.headers.get("Content-Type", ""):
            with open(output_file, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            if os.path.exists(output_file) and os.path.getsize(output_file) > 100_000:
                print("  Engine 1: Direct CDN download succeeded!")
                return True
        print(f"  Engine 1: CDN blocked (status={resp.status_code}). Trying SoundCloud fallback...")
    except Exception as e:
        print(f"  Engine 1: CDN exception: {e}")

    _cleanup_temp(output_file)

    # ── Try 2: SoundCloud search fallback ──
    search_title = re.split(r"\s*[\|\[{]", title)[0].strip()
    for query in [f"scsearch1:{search_title} NCS", f"scsearch1:{search_title} no copyright"]:
        print(f"  Engine 1 fallback: SoundCloud search for '{search_title}'...")
        cmd = [
            "yt-dlp", "--no-playlist",
            "--user-agent", random.choice(HUMAN_USER_AGENTS),
            "-f", "bestaudio/best",
            "--extract-audio", "--audio-format", "wav", "--audio-quality", "0",
            "--output", output_file,
            query,
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if os.path.exists(output_file) and os.path.getsize(output_file) > 100_000:
                print("  Engine 1: SoundCloud fallback succeeded!")
                return True
            _cleanup_temp(output_file)
        except subprocess.TimeoutExpired:
            print("  Engine 1: SoundCloud search timed out.")
        except Exception as e:
            print(f"  Engine 1: SoundCloud exception: {e}")

    return False


# ─────────────────────────────────────────────────────────
# ENGINE 2: Invidious (YouTube proxy — bypasses bot block)
#   NEW: Replaces reliance on broken Cobalt-only approach
#   Gets direct audio CDN URLs — no YouTube bot detection
# ─────────────────────────────────────────────────────────
def _get_ncs_videos_via_invidious():
    import requests
    instances = INVIDIOUS_INSTANCES[:]
    random.shuffle(instances)
    for instance in instances:
        try:
            url = f"{instance}/api/v1/search?q=NCS+No+Copyright+Sounds&type=video&page=1&sort_by=upload_date"
            resp = requests.get(url, timeout=20,
                                headers={"User-Agent": random.choice(HUMAN_USER_AGENTS)})
            if resp.status_code == 200:
                data = resp.json()
                videos = [
                    {"id": v["videoId"], "title": v["title"], "genre": detect_genre(v["title"]),
                     "instance": instance}
                    for v in data
                    if v.get("type") == "video" and "NCS" in v.get("title", "").upper()
                ]
                if videos:
                    print(f"  Engine 2: Got {len(videos)} NCS videos via {instance}")
                    return videos, instance
        except Exception as e:
            print(f"  Engine 2: Invidious {instance} failed: {e}")
    return [], None


def download_via_invidious(video_id, instance, output_file):
    import requests
    try:
        url = f"{instance}/api/v1/videos/{video_id}"
        resp = requests.get(url, timeout=20,
                            headers={"User-Agent": random.choice(HUMAN_USER_AGENTS)})
        if resp.status_code != 200:
            return False
        data = resp.json()
        audio_formats = [f for f in data.get("adaptiveFormats", [])
                         if f.get("type", "").startswith("audio/")]
        if not audio_formats:
            return False
        audio_formats.sort(key=lambda x: x.get("bitrate", 0), reverse=True)
        stream_url = audio_formats[0].get("url")
        if not stream_url:
            return False

        print(f"  Engine 2: Downloading audio via Invidious stream...")
        r = requests.get(stream_url, stream=True, timeout=180,
                         headers={"User-Agent": random.choice(HUMAN_USER_AGENTS),
                                  "Referer": instance})
        if r.status_code == 200:
            raw_file = output_file.replace(".wav", ".webm")
            with open(raw_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            if os.path.exists(raw_file) and os.path.getsize(raw_file) > 100_000:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", raw_file, "-ac", "2", "-ar", "44100", output_file],
                    capture_output=True, timeout=120
                )
                _cleanup_temp(raw_file)
                if os.path.exists(output_file) and os.path.getsize(output_file) > 100_000:
                    print("  Engine 2: Invidious download succeeded!")
                    return True
    except Exception as e:
        print(f"  Engine 2: Invidious download error: {e}")
    return False


# ─────────────────────────────────────────────────────────
# ENGINE 3: SoundCloud via yt-dlp (less blocked than YouTube)
# ─────────────────────────────────────────────────────────
def fetch_videos_via_ytdlp(source_url, limit=40, use_cookies=True):
    cmd = [
        "yt-dlp", "--dump-json", "--flat-playlist",
        "--playlist-end", str(limit),
        "--user-agent", random.choice(HUMAN_USER_AGENTS),
        source_url,
    ]
    if use_cookies and os.path.exists(COOKIES_FILE):
        cmd.extend(["--cookies", COOKIES_FILE])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data   = json.loads(line)
                vid_id = data.get("id", "")
                title  = data.get("title", "")
                if vid_id and title:
                    if "youtube.com" in source_url or "youtu.be" in source_url:
                        v_url = f"https://www.youtube.com/watch?v={vid_id}"
                    else:
                        v_url = data.get("url") or data.get("webpage_url") or source_url
                    videos.append({"id": vid_id, "title": title, "url": v_url,
                                   "genre": detect_genre(title)})
            except json.JSONDecodeError:
                pass
        return videos
    except Exception as e:
        print(f"  yt-dlp listing error ({source_url}): {e}")
        return []


def download_via_soundcloud(url, output_file):
    cmd = [
        "yt-dlp", "--no-playlist",
        "--user-agent", random.choice(HUMAN_USER_AGENTS),
        "-f", "bestaudio/best",
        "--extract-audio", "--audio-format", "wav", "--audio-quality", "0",
        "--output", output_file,
        url,
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return os.path.exists(output_file) and os.path.getsize(output_file) > 100_000
    except Exception as e:
        print(f"  SoundCloud download error: {e}")
        return False


# ─────────────────────────────────────────────────────────
# ENGINE 4: Cobalt API (fixed — dead co.wuk.sh removed)
# ─────────────────────────────────────────────────────────
def download_via_cobalt(url, output_file):
    import requests
    print("Engine 4: Cobalt API (updated instances)...")
    headers = {
        "Accept":       "application/json",
        "Content-Type": "application/json",
        "User-Agent":   random.choice(HUMAN_USER_AGENTS),
    }
    payload = {"url": url, "downloadMode": "audio", "audioFormat": "mp3", "audioBitrate": "320"}

    instances = COBALT_INSTANCES[:]
    random.shuffle(instances)
    for api_url in instances:
        try:
            resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
            if resp.status_code != 200:
                print(f"  Cobalt {api_url} returned {resp.status_code}")
                continue
            data   = resp.json()
            status = data.get("status", "")
            if status in ("tunnel", "redirect", "stream"):
                stream_url = data.get("url")
                if not stream_url:
                    continue
                s_resp = requests.get(stream_url, stream=True, timeout=120,
                                      headers={"User-Agent": random.choice(HUMAN_USER_AGENTS)})
                if s_resp.status_code == 200:
                    mp3_file = output_file.replace(".wav", ".mp3")
                    with open(mp3_file, "wb") as f:
                        for chunk in s_resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    if os.path.exists(mp3_file) and os.path.getsize(mp3_file) > 100_000:
                        subprocess.run(
                            ["ffmpeg", "-y", "-i", mp3_file, output_file],
                            capture_output=True, timeout=60
                        )
                        _cleanup_temp(mp3_file)
                        if os.path.exists(output_file) and os.path.getsize(output_file) > 100_000:
                            print(f"  Engine 4: Cobalt succeeded via {api_url}")
                            return True
            else:
                err = (data.get("error") or {}).get("code", "") or data.get("text", "unknown")
                print(f"  Cobalt ({api_url}) error: {err}")
        except Exception as e:
            print(f"  Cobalt ({api_url}) exception: {e}")
    return False


# ─────────────────────────────────────────────────────────
# ENGINE 5: yt-dlp iOS player client bypass
#   NEW: Replaces Tor-only approach (Tor unavailable on GitHub Actions)
#   Uses iOS player client to bypass YouTube bot detection
#   Falls back to Tor if available
# ─────────────────────────────────────────────────────────
def download_via_ios_bypass(url, output_file):
    """yt-dlp with iOS extractor args — bypasses YouTube 403 bot block."""
    print(f"  Engine 5: iOS player client bypass...")
    cmd = [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=ios,mweb",
        "--user-agent", random.choice(HUMAN_USER_AGENTS),
        "-f", "bestaudio/best",
        "--extract-audio", "--audio-format", "wav", "--audio-quality", "0",
        "--no-playlist",
        "--output", output_file,
        url,
    ]
    if os.path.exists(COOKIES_FILE):
        cmd.extend(["--cookies", COOKIES_FILE])
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        if os.path.exists(output_file) and os.path.getsize(output_file) > 100_000:
            print("  Engine 5: iOS bypass succeeded!")
            return True
    except Exception as e:
        print(f"  Engine 5: iOS bypass error: {e}")
    return False


def _is_tor_running():
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 9050), timeout=3):
            return True
    except OSError:
        return False


def download_via_tor_youtube(yt_videos, history, output_file):
    if not _is_tor_running():
        print("  Tor not running — Tor fallback skipped.")
        return None

    fresh = [v for v in yt_videos if v["id"] not in history]
    candidates = (fresh[:5] if fresh else yt_videos[:5])
    random.shuffle(candidates)

    for video in candidates:
        wait = random.uniform(8, 25)
        print(f"  [Tor] Waiting {wait:.1f}s... Trying: {video['title']}")
        time.sleep(wait)
        user_agent = random.choice(HUMAN_USER_AGENTS)
        cmd = [
            "yt-dlp",
            "--proxy", TOR_PROXY,
            "--user-agent", user_agent,
            "--extractor-args", "youtube:player_client=ios,mweb",
            "--limit-rate", "200K",
            "-f", "bestaudio/best",
            "--extract-audio", "--audio-format", "wav", "--audio-quality", "0",
            "--retries", "2", "--no-playlist",
            "--output", output_file,
            video["url"],
        ]
        if os.path.exists(COOKIES_FILE):
            cmd.extend(["--cookies", COOKIES_FILE])
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if os.path.exists(output_file) and os.path.getsize(output_file) > 100_000:
                print(f"  Engine 5 Tor: Succeeded: {video['title']}")
                return video["title"], video["genre"], video["id"]
            _cleanup_temp(output_file)
        except subprocess.TimeoutExpired:
            print("  [Tor] Timed out.")
        except Exception as e:
            print(f"  [Tor] Exception: {e}")
        try:
            subprocess.run(["sudo", "killall", "-HUP", "tor"], capture_output=True, timeout=5)
            time.sleep(random.uniform(5, 10))
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────
def download_random_ncs_song(output_dir="downloads"):
    """
    Multi-Engine NCS Downloader (5 engines):
      1. NCS.io direct CDN + SoundCloud fallback
      2. Invidious YouTube proxy (no bot detection)
      3. SoundCloud via yt-dlp
      4. Cobalt API (fixed — dead instances removed)
      5. yt-dlp iOS player client bypass + Tor fallback
    Returns (audio_path, title, genre)
    """
    os.makedirs(output_dir, exist_ok=True)
    history    = load_history()
    audio_file = os.path.join(output_dir, "audio.wav")
    _cleanup_temp(audio_file)

    # ── ENGINE 1: NCS.io direct CDN + SoundCloud fallback ──
    print("\n>>> ENGINE 1: NCS.io direct download + SoundCloud fallback")
    ncs_tracks = fetch_tracks_from_ncs_io()
    if ncs_tracks:
        random.shuffle(ncs_tracks)
        fresh = [t for t in ncs_tracks if str(t["id"]) not in history]
        chosen = fresh[0] if fresh else ncs_tracks[0]
        if download_from_ncs_io(chosen["id"], chosen["title"], audio_file):
            save_to_history(chosen["id"])
            return audio_file, chosen["title"], chosen["genre"]
        print("  Engine 1 failed.")
    else:
        print("  Engine 1: No tracks from NCS.io.")
    _cleanup_temp(audio_file)

    # ── ENGINE 2: Invidious (YouTube proxy) ───────────────
    print("\n>>> ENGINE 2: Invidious YouTube proxy (bot detection bypass)")
    yt_videos_inv, inv_instance = _get_ncs_videos_via_invidious()
    if yt_videos_inv and inv_instance:
        fresh_inv = [v for v in yt_videos_inv if v["id"] not in history]
        chosen_inv = random.choice(fresh_inv) if fresh_inv else random.choice(yt_videos_inv)
        if download_via_invidious(chosen_inv["id"], inv_instance, audio_file):
            save_to_history(chosen_inv["id"])
            genre_inv = chosen_inv["genre"]
            if is_generic_genre(genre_inv):
                genre_inv = infer_genre_from_ncs_tracks(chosen_inv["title"], ncs_tracks)
            return audio_file, chosen_inv["title"], genre_inv
        print("  Engine 2 failed.")
    else:
        print("  Engine 2: No Invidious instances responded.")
    _cleanup_temp(audio_file)

    # ── ENGINE 3: SoundCloud via yt-dlp ──────────────────
    print("\n>>> ENGINE 3: SoundCloud via yt-dlp (less restricted than YouTube)")
    sc_tracks = fetch_videos_via_ytdlp(NCS_SOUNDCLOUD, limit=50, use_cookies=False)
    if sc_tracks:
        random.shuffle(sc_tracks)
        fresh_sc = [t for t in sc_tracks if t["id"] not in history]
        chosen_sc = fresh_sc[0] if fresh_sc else sc_tracks[0]
        print(f"  Trying: {chosen_sc['title']}")
        if download_via_soundcloud(chosen_sc["url"], audio_file):
            save_to_history(chosen_sc["id"])
            genre_sc = chosen_sc["genre"]
            if is_generic_genre(genre_sc):
                genre_sc = infer_genre_from_ncs_tracks(chosen_sc["title"], ncs_tracks)
            if is_generic_genre(genre_sc):
                genre_sc = lookup_genre_from_ncs_io(chosen_sc["title"])
            return audio_file, chosen_sc["title"], genre_sc
        print("  Engine 3 failed.")
    else:
        print("  Engine 3: No SoundCloud tracks found.")
    _cleanup_temp(audio_file)

    # Fetch YouTube list for engines 4 & 5
    print("\n>>> Fetching YouTube video list for engines 4 & 5...")
    yt_videos = fetch_videos_via_ytdlp(NCS_YOUTUBE, limit=30, use_cookies=True)
    print(f"  Found {len(yt_videos)} YouTube videos." if yt_videos else "  YouTube list unavailable.")

    # ── ENGINE 4: Cobalt API (fixed) ─────────────────────
    print("\n>>> ENGINE 4: Cobalt API (updated — dead instances removed)")
    if yt_videos:
        fresh_yt = [v for v in yt_videos if v["id"] not in history]
        chosen_yt = random.choice(fresh_yt) if fresh_yt else random.choice(yt_videos)
        if download_via_cobalt(chosen_yt["url"], audio_file):
            save_to_history(chosen_yt["id"])
            genre_yt = chosen_yt["genre"]
            if is_generic_genre(genre_yt):
                genre_yt = infer_genre_from_ncs_tracks(chosen_yt["title"], ncs_tracks)
            return audio_file, chosen_yt["title"], genre_yt
        print("  Engine 4 failed.")
    else:
        print("  Engine 4 skipped (no YouTube URLs).")
    _cleanup_temp(audio_file)

    # ── ENGINE 5: iOS bypass + Tor fallback ──────────────
    print("\n>>> ENGINE 5: yt-dlp iOS player client bypass")
    if yt_videos:
        fresh_yt2 = [v for v in yt_videos if v["id"] not in history]
        chosen_yt2 = random.choice(fresh_yt2) if fresh_yt2 else random.choice(yt_videos)
        if download_via_ios_bypass(chosen_yt2["url"], audio_file):
            save_to_history(chosen_yt2["id"])
            return audio_file, chosen_yt2["title"], chosen_yt2["genre"]
        print("  iOS bypass failed. Trying Tor fallback...")
        _cleanup_temp(audio_file)
        result = download_via_tor_youtube(yt_videos, history, audio_file)
        if result:
            title_tor, genre_tor, vid_id_tor = result
            save_to_history(vid_id_tor)
            return audio_file, title_tor, genre_tor
        print("  Engine 5 failed.")
    else:
        print("  Engine 5 skipped (no YouTube URLs).")
    _cleanup_temp(audio_file)

    print("\n❌ All Engines Failed. No audio could be downloaded.")
    return None, None, None


if __name__ == "__main__":
    audio_path, title, genre = download_random_ncs_song()
    if title:
        print(f"\n✅ Success! {title} [{genre}] -> {audio_path}")
    else:
        print("\n❌ Download failed.")
