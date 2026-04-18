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
        api_url = "https://api.cobalt.tools/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
    extractor_args = "youtube:player-client=web,android"
    
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
                    if "|" in title:
                        parts = [p.strip() for p in title.split("|")]
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
        chosen = next((v for v in videos if v['id'] not in history), None)
                
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
                print("All Engines Failed. Check logs.")
                return None, None, None

        if os.path.exists(audio_file):
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(chosen['id'] + "\n")
            return audio_file, chosen['title'], chosen['genre']
        print(f"Engine Exception: {e}")
        return None, None
            
    except subprocess.CalledProcessError as e:
        print(f"Command Error: yt-dlp failed with exit code {e.returncode}.")
        if getattr(e, 'stderr', None):
            print(f"yt-dlp STDERR: {e.stderr}")
        return None, None
    except Exception as e:
        print(f"Error downloading: {e}")
        return None, None

if __name__ == "__main__":
    audio_path, title = download_random_ncs_song()
    if title:
        print(f"Success! Ready for visualizer: {title}")
