import subprocess
import random
import os
import json

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
        if os.path.exists(audio_file):
            os.remove(audio_file)
            
        dl_cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "wav", 
            "--audio-quality", "0",
            "--extractor-args", extractor_args,
            "--rm-cache-dir",
            "--output", audio_file,
            target_v_url
        ]
        
        if os.path.exists(cookies_file):
            dl_cmd.extend(["--cookies", cookies_file])
        
        print("Downloading High-Quality audio...")
        dl_result = subprocess.run(dl_cmd, capture_output=True, text=True)
        
        if dl_result.returncode == 0 and os.path.exists(audio_file):
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(chosen['id'] + "\n")
            return audio_file, chosen['title'], chosen['genre']
        else:
            print(f"ERROR: Engine 1 (Direct) failed with code {dl_result.returncode}")
            print("--- STDERR ---")
            print(dl_result.stderr[-1000:] if dl_result.stderr else "No error output")
            print("--------------")
            return None, None, None
            
    except Exception as e:
        print(f"Engine Exception: {e}")
        return None, None, None
            
    except Exception as e:
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
