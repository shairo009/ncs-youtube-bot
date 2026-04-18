import subprocess
import random
import os
import json

def download_random_ncs_song(output_dir="downloads"):
    """
    Fetches the latest videos from the official NCS YouTube channel and downloads
    a random one as a high-quality WAV file.
    """
    os.makedirs(output_dir, exist_ok=True)
    print("Fetching list of latest NCS videos from YouTube...")
    
    # Target official NCS YouTube Videos
    ncs_url = "https://www.youtube.com/@NoCopyrightSounds/videos"
    cookies_file = "cookies.txt"
    
    # 1. Fetch JSON data of latest 50 videos
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--playlist-end", "50",
        ncs_url
    ]
    
    # Use cookies if available
    if os.path.exists(cookies_file):
        cmd.extend(["--cookies", cookies_file])
        print("Using cookies.txt for authentication.")

    try:
        print("Running yt-dlp to fetch video list...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line: continue
            try:
                data = json.loads(line)
                # Ensure it's a real video from the NCS channel
                if data.get("id") and data.get("title") and data.get("url"):
                    uploader = data.get("uploader") or ""
                    if "NoCopyrightSounds" in uploader or "@NoCopyrightSounds" in ncs_url:
                        videos.append({"id": data["id"], "title": data["title"], "url": data["url"] or f"https://www.youtube.com/watch?v={data['id']}"})
            except json.JSONDecodeError:
                pass
        
        if not videos:
            print("Error: No videos found. YouTube might be blocking the request.")
            return None, None
            
        print(f"Found {len(videos)} videos. Finding a fresh one...")
        
        # Load History
        history_file = "downloads_history.txt"
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = f.read().splitlines()
        else:
            history = []
            
        random.shuffle(videos)
        chosen = None
        for v in videos:
            if v['id'] not in history:
                chosen = v
                break
                
        if not chosen:
            print("Notice: No fresh videos found. Resetting history or increasing limit is recommended.")
            return None, None
        
        # Save to history
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(chosen['id'] + "\n")
            
        target_v_url = chosen['url']
        print(f"Selected: {chosen['title']} ({target_v_url})")
        
        audio_file = os.path.join(output_dir, "audio.wav")
        if os.path.exists(audio_file):
            os.remove(audio_file)
            
        # 2. High Quality Download Command
        dl_cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "wav", 
            "--audio-quality", "0",      # Highest quality (320kbps equivalent)
            "--rm-cache-dir",            # Fresh state
            "--output", audio_file
        ]
        
        if os.path.exists(cookies_file):
            dl_cmd.extend(["--cookies", cookies_file])
            
        dl_cmd.append(target_v_url)
        
        print("Downloading High-Quality audio...")
        subprocess.run(dl_cmd, capture_output=True, text=True, check=True)
        
        if os.path.exists(audio_file):
            print(f"Download complete: {audio_file}")
            return audio_file, chosen['title']
        else:
            print("Download failed.")
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
