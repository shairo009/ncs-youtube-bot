import subprocess
import random
import os
import json

def download_audio_via_cobalt(url, output_file):
    """
    Fallback Engine: Download via Cobalt API (Bypasses CI/CD IP blocks).
    """
    import requests
    print("Engine 2: Attempting download via Cobalt API...")
    try:
        api_url = "https://api.cobalt.tools/"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "downloadMode": "audio",
            "audioFormat": "wav",
            "audioBitrate": "320"
        }
        resp = requests.post(api_url, json=payload, headers=headers)
        data = resp.json()
        
        if data.get("status") == "stream":
            stream_url = data.get("url")
            print("Cobalt Stream URL found. Downloading...")
            s_resp = requests.get(stream_url, stream=True)
            with open(output_file, 'wb') as f:
                for chunk in s_resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            print(f"Cobalt Error: {data.get('text', 'Unknown Error')}")
            return False
    except Exception as e:
        print(f"Cobalt Exception: {e}")
        return False

def download_random_ncs_song(output_dir="downloads"):
    """
    Robust Multi-Engine Downloader with Genre Detection:
    Returns (audio_path, title, genre).
    """
    os.makedirs(output_dir, exist_ok=True)
    print("Fetching list of latest NCS videos from YouTube...")
    
    ncs_url = "https://www.youtube.com/@NoCopyrightSounds/videos"
    cookies_file = "cookies.txt"
    extractor_args = "youtube:player-client=ios"
    
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--playlist-end", "40",
        "--extractor-args", extractor_args,
        ncs_url
    ]
    
    if os.path.exists(cookies_file):
        cmd.extend(["--cookies", cookies_file])

    try:
        print("Running yt-dlp to fetch video list...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line: continue
            try:
                data = json.loads(line)
                title = data.get("title") or ""
                uploader = data.get("uploader") or ""
                if data.get("id") and title:
                    v_url = data.get("url") or f"https://www.youtube.com/watch?v={data['id']}"
                    
                    # Detect Genre from Title or Metadata
                    # Pattern: Artist - Song | Genre | NCS - ...
                    genre = "NCS Release"
                    # Handle both standard '|' and full-width '｜' pipes
                    title_clean = title.replace("｜", "|")
                    if "|" in title_clean:
                        parts = [p.strip() for p in title_clean.split("|")]
                        if len(parts) >= 2:
                            # Typically second or third part is genre
                            genre = parts[1]
                    
                    if "NoCopyrightSounds" in uploader or "@NoCopyrightSounds" in ncs_url:
                        videos.append({
                            "id": data["id"], 
                            "title": title, 
                            "url": v_url,
                            "genre": genre
                        })
            except json.JSONDecodeError:
                pass
        
        if not videos:
            print("Error: No videos found.")
            return None, None, None
            
        print(f"Found {len(videos)} videos. Selecting a fresh one...")
        
        history_file = "downloads_history.txt"
        history = []
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = f.read().splitlines()
            
        random.shuffle(videos)
        
        # Read last genre to avoid repetition
        last_genre_file = "last_genre.txt"
        last_genre = ""
        if os.path.exists(last_genre_file):
            with open(last_genre_file, 'r', encoding='utf-8') as f:
                last_genre = f.read().strip()
                
        fresh_videos = [v for v in videos if v['id'] not in history]
        
        # Filter by genre (rotation)
        filtered_videos = [v for v in fresh_videos if v['genre'].lower() != last_genre.lower()]
        
        # Selection: Try filtered first, then fallback to any fresh video
        chosen = None
        if filtered_videos:
            print(f"🔄 Rotating color: Skipping last genre '{last_genre}'")
            chosen = random.choice(filtered_videos)
        elif fresh_videos:
            print(f"⚠️ Notice: All fresh videos are '{last_genre}'. Color rotation skipped.")
            chosen = random.choice(fresh_videos)
            
        if not chosen:
            print("Notice: No fresh videos found.")
            return None, None, None
        
        target_v_url = chosen['url']
        print(f"Selected: {chosen['title']} (Genre: {chosen['genre']})")
        
        audio_file = os.path.join(output_dir, "audio.wav")
        if os.path.exists(audio_file): os.remove(audio_file)
            
        # ENGINE 1: Direct yt-dlp
        print("Engine 1: Attempting Direct Download...")
        dl_cmd = [
            "yt-dlp", "-f", "bestaudio/best", "--extract-audio", "--audio-format", "wav", 
            "--audio-quality", "0", "--extractor-args", extractor_args, "--output", audio_file, target_v_url
        ]
        if os.path.exists(cookies_file): dl_cmd.extend(["--cookies", cookies_file])
        
        dl_result = subprocess.run(dl_cmd, capture_output=True, text=True)
        
        if dl_result.returncode == 0 and os.path.exists(audio_file):
            print("Engine 1 Success.")
        else:
            print("Engine 1 Failed (Likely IP Block). Switching to Fallback...")
            # ENGINE 2: Cobalt Fallback
            success = download_audio_via_cobalt(target_v_url, audio_file)
            if not success:
                print("All online engines failed. Checking for local fallback...")
                # CHECK FOR LOCAL FALLBACK
                local_files = [f for f in os.listdir(output_dir) if f.endswith(('.wav', '.mp3'))]
                if local_files:
                    # Pick a random local file but avoid audio.wav if it's empty
                    valid_files = [f for f in local_files if f != "audio.wav" or os.path.getsize(os.path.join(output_dir, f)) > 0]
                    if valid_files:
                        chosen_local = random.choice(valid_files)
                        print(f"✅ Found local song fallback: {chosen_local}")
                        
                        # Extract genre from local filename if possible
                        local_genre = "NCS Release"
                        local_title_clean = chosen_local.replace("｜", "|")
                        if "|" in local_title_clean:
                            parts = [p.strip() for p in local_title_clean.split("|")]
                            if len(parts) >= 2:
                                local_genre = parts[1]
                        
                        return os.path.join(output_dir, chosen_local), chosen_local, local_genre
                
                print("❌ All Engines and Local Fallback Failed. Check logs.")
                return None, None, None

        if os.path.exists(audio_file):
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(chosen['id'] + "\n")
            return audio_file, chosen['title'], chosen['genre']
        print("Engine Error: No audio file was created.")
        return None, None, None
            
    except subprocess.CalledProcessError as e:
        print(f"Command Error: yt-dlp failed with exit code {e.returncode}.")
        if getattr(e, 'stderr', None):
            print(f"yt-dlp STDERR: {e.stderr}")
        return None, None, None
    except Exception as e:
        print(f"Error downloading: {e}")
        return None, None, None

if __name__ == "__main__":
    audio_path, title = download_random_ncs_song()
    if title:
        print(f"Success! Ready for visualizer: {title}")
