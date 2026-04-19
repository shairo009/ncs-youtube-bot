import subprocess
import random
import os
import json

HISTORY_FILE = "downloads_history.txt"
COOKIES_FILE = "cookies.txt"
EXTRACTOR_ARGS = "youtube:player-client=web,android"
NCS_SOUNDCLOUD = "https://soundcloud.com/nocopyrightsounds"
NCS_YOUTUBE = "https://www.youtube.com/@NoCopyrightSounds/videos"


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return set(f.read().splitlines())
    return set()


def save_to_history(track_id):
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(str(track_id) + "\n")


def detect_genre(title):
    """Detect genre from NCS title pattern: Artist - Song | Genre | NCS - ..."""
    genre = "NCS Release"
    title_clean = title.replace("\uff5c", "|")
    if "|" in title_clean:
        parts = [p.strip() for p in title_clean.split("|")]
        if len(parts) >= 2:
            genre = parts[1]
    return genre


# ─────────────────────────────────────────
# ENGINE 1: NCS official website (ncs.io)
# ─────────────────────────────────────────
def fetch_tracks_from_ncs_io():
    """
    Fetch track list from NCS official website (ncs.io/music-search).
    Uses data-artistraw, data-track, data-genre attributes directly.
    """
    try:
        import requests
        from bs4 import BeautifulSoup

        print("Engine 1: Fetching tracks from NCS official website (ncs.io)...")
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        offset = random.choice([0, 15, 30, 45, 60, 75, 90, 105, 120])
        url = f"https://ncs.io/music-search?q=&genre=&mood=&version=&offset={offset}"

        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        tracks = []
        seen_ids = set()

        # Primary: use data-artistraw + data-track + data-genre (actual NCS.io HTML structure)
        for item in soup.find_all(attrs={"data-tid": True}):
            track_id = item.get("data-tid", "").strip()
            if not track_id or track_id in seen_ids:
                continue
            seen_ids.add(track_id)

            artist   = item.get("data-artistraw", "").strip()
            track    = item.get("data-track", "").strip()
            genre    = item.get("data-genre", "").strip() or "NCS Release"

            if artist and track:
                title = f"{artist} - {track}"
                tracks.append({"id": track_id, "title": title, "genre": genre})
            elif track:
                tracks.append({"id": track_id, "title": track, "genre": genre})

        print(f"NCS.io: Found {len(tracks)} tracks at offset {offset}")
        return tracks

    except Exception as e:
        print(f"NCS.io fetch error: {e}")
        return []


def download_from_ncs_io(track_id, title, output_file):
    """
    Download NCS track audio using yt-dlp YouTube search.
    NCS.io direct download requires login, so we search YouTube instead.
    """
    print(f"  Searching YouTube for '{title}'...")

    # Build a clean search query: "Artist - Track NCS" (remove brackets/pipes)
    search_title = re.split(r'\s*[\|\[{]', title)[0].strip()
    search_query = f"ytsearch1:{search_title} NCS"

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bestaudio/best",
        "--extract-audio", "--audio-format", "wav",
        "--audio-quality", "0",
        "--output", output_file,
        "--match-filter", "duration < 600",
        search_query,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if os.path.exists(output_file) and os.path.getsize(output_file) > 100_000:
            print(f"  Engine 1 Success (YouTube search for NCS.io track)")
            return True
        if result.returncode != 0:
            print(f"  Engine 1 yt-dlp error: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print("  Engine 1 search timed out")
    except Exception as e:
        print(f"  Engine 1 exception: {e}")

    return False


# ──────────────────────────────────────────────────────
# ENGINE 2: Cobalt API (FIXED — updated 2024/2025 format)
# ──────────────────────────────────────────────────────
def download_via_cobalt(url, output_file):
    """Download via Cobalt API using the updated v10+ format."""
    import requests

    print("Engine 2: Attempting download via Cobalt API (updated format)...")

    cobalt_instances = [
        "https://api.cobalt.tools/",
        "https://cobalt.api.timelessnesses.me/",
        "https://co.wuk.sh/",
    ]

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    payload = {
        "url": url,
        "downloadMode": "audio",
        "audioFormat": "wav",
        "audioBitrate": "320",
    }

    for api_url in cobalt_instances:
        try:
            resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
            data = resp.json()
            status = data.get("status", "")

            # New API returns 'tunnel' or 'redirect'; old returned 'stream'
            if status in ("tunnel", "redirect", "stream"):
                stream_url = data.get("url")
                if not stream_url:
                    continue
                print(f"  Cobalt: Got '{status}' URL, downloading...")
                s_resp = requests.get(
                    stream_url, stream=True, timeout=120,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                with open(output_file, "wb") as f:
                    for chunk in s_resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                if os.path.exists(output_file) and os.path.getsize(output_file) > 100_000:
                    print(f"  Engine 2 Success via {api_url}")
                    return True
                if os.path.exists(output_file):
                    os.remove(output_file)
            else:
                err = (data.get("error") or {}).get("code", "") or data.get("text", "unknown")
                print(f"  Cobalt ({api_url}) error: {err}")

        except Exception as e:
            print(f"  Cobalt ({api_url}) exception: {e}")
            continue

    return False


# ──────────────────────────────────────────────────────
# ENGINE 3 + 4: yt-dlp helpers
# ──────────────────────────────────────────────────────
def fetch_videos_via_ytdlp(source_url, limit=40, use_cookies=True):
    """Fetch video list from YouTube or SoundCloud via yt-dlp."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--playlist-end", str(limit),
        source_url,
    ]
    if use_cookies and os.path.exists(COOKIES_FILE):
        cmd.extend(["--cookies", COOKIES_FILE])
    if "youtube.com" in source_url:
        cmd.extend(["--extractor-args", EXTRACTOR_ARGS])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                vid_id = data.get("id", "")
                title = data.get("title", "")
                if vid_id and title:
                    if "youtube.com" in source_url or "youtu.be" in source_url:
                        v_url = f"https://www.youtube.com/watch?v={vid_id}"
                    else:
                        v_url = data.get("url") or data.get("webpage_url") or source_url
                    videos.append({
                        "id": vid_id,
                        "title": title,
                        "url": v_url,
                        "genre": detect_genre(title),
                    })
            except json.JSONDecodeError:
                pass
        return videos
    except Exception as e:
        print(f"  yt-dlp listing error ({source_url}): {e}")
        return []


def download_via_ytdlp(url, output_file, use_cookies=True):
    """Download audio via yt-dlp."""
    cmd = [
        "yt-dlp", "-f", "bestaudio/best",
        "--extract-audio", "--audio-format", "wav",
        "--audio-quality", "0",
        "--output", output_file,
        url,
    ]
    if use_cookies and os.path.exists(COOKIES_FILE):
        cmd.extend(["--cookies", COOKIES_FILE])
    if "youtube.com" in url or "youtu.be" in url:
        cmd.extend(["--extractor-args", EXTRACTOR_ARGS])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 100_000:
            return True
        if result.returncode != 0:
            print(f"  yt-dlp stderr: {result.stderr[:400]}")
    except subprocess.TimeoutExpired:
        print("  yt-dlp timed out")
    except Exception as e:
        print(f"  yt-dlp exception: {e}")
    return False


# ──────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────────────
def download_random_ncs_song(output_dir="downloads"):
    """
    Multi-Engine Downloader — tries each engine in order:
      1. NCS official website (ncs.io) — primary, no IP block
      2. Cobalt API (updated 2024 format) + YouTube video URL
      3. yt-dlp on NCS SoundCloud (less strict than YouTube)
      4. yt-dlp direct YouTube (last resort)
    Returns (audio_path, title, genre)
    """
    os.makedirs(output_dir, exist_ok=True)
    history = load_history()

    audio_file = os.path.join(output_dir, "audio.wav")
    if os.path.exists(audio_file):
        os.remove(audio_file)

    # ── ENGINE 1: NCS.io ──────────────────────────────
    print("\n>>> ENGINE 1: NCS official website (ncs.io)")
    ncs_tracks = fetch_tracks_from_ncs_io()
    if ncs_tracks:
        random.shuffle(ncs_tracks)
        fresh = [t for t in ncs_tracks if str(t["id"]) not in history]
        chosen = fresh[0] if fresh else ncs_tracks[0]

        if download_from_ncs_io(chosen["id"], chosen["title"], audio_file):
            save_to_history(chosen["id"])
            return audio_file, chosen["title"], chosen["genre"]
        print("  Engine 1 download failed.")
    else:
        print("  Engine 1: No tracks fetched from ncs.io.")

    # Fetch YouTube video list (needed for engines 2 & 4)
    print("\n>>> Fetching YouTube video list for engines 2 & 4...")
    yt_videos = fetch_videos_via_ytdlp(NCS_YOUTUBE, limit=30, use_cookies=True)
    if yt_videos:
        print(f"  Found {len(yt_videos)} YouTube videos.")
    else:
        print("  Could not fetch YouTube list (IP block likely).")

    # ── ENGINE 2: Cobalt API + YouTube URL ────────────
    print("\n>>> ENGINE 2: Cobalt API (updated format)")
    if yt_videos:
        random.shuffle(yt_videos)
        fresh_yt = [v for v in yt_videos if v["id"] not in history]
        chosen_yt = fresh_yt[0] if fresh_yt else yt_videos[0]

        if download_via_cobalt(chosen_yt["url"], audio_file):
            save_to_history(chosen_yt["id"])
            return audio_file, chosen_yt["title"], chosen_yt["genre"]
        print("  Engine 2 failed.")
    else:
        print("  Engine 2 skipped (no YouTube URLs).")

    # ── ENGINE 3: yt-dlp on NCS SoundCloud ────────────
    print("\n>>> ENGINE 3: yt-dlp on NCS SoundCloud")
    sc_tracks = fetch_videos_via_ytdlp(NCS_SOUNDCLOUD, limit=50, use_cookies=False)
    if sc_tracks:
        random.shuffle(sc_tracks)
        fresh_sc = [t for t in sc_tracks if t["id"] not in history]
        chosen_sc = fresh_sc[0] if fresh_sc else sc_tracks[0]
        print(f"  Trying: {chosen_sc['title']}")

        if download_via_ytdlp(chosen_sc["url"], audio_file, use_cookies=False):
            save_to_history(chosen_sc["id"])
            return audio_file, chosen_sc["title"], chosen_sc["genre"]
        print("  Engine 3 failed.")
    else:
        print("  Engine 3: No SoundCloud tracks found.")

    # ── ENGINE 4: yt-dlp direct YouTube ───────────────
    print("\n>>> ENGINE 4: yt-dlp direct YouTube (last resort)")
    if yt_videos:
        fresh_yt2 = [v for v in yt_videos if v["id"] not in history]
        chosen_yt2 = fresh_yt2[0] if fresh_yt2 else yt_videos[0]
        print(f"  Trying: {chosen_yt2['title']}")

        if download_via_ytdlp(chosen_yt2["url"], audio_file, use_cookies=True):
            save_to_history(chosen_yt2["id"])
            return audio_file, chosen_yt2["title"], chosen_yt2["genre"]
        print("  Engine 4 failed.")

    print("\n\u274c All Engines Failed. No audio could be downloaded.")
    return None, None, None


if __name__ == "__main__":
    audio_path, title, genre = download_random_ncs_song()
    if title:
        print(f"\n\u2705 Success! Ready for visualizer: {title} [{genre}]")
