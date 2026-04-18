import subprocess
import random
import os
import json

def download_random_ncs_song(output_dir="downloads"):
    """
    Fetches the last 50 videos from NoCopyrightSounds and downloads a random one
    as a WAV file for audio processing in the visualizer.
    """
    os.makedirs(output_dir, exist_ok=True)
    print("Fetching list of latest NCS videos...")
    
    # Target NCS YouTube channel
    ncs_url = "https://www.youtube.com/@NoCopyrightSounds/videos"
    
    # 1. Fetch JSON data of latest 50 videos to reliably get Title and ID
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--playlist-end", "50",
        ncs_url
    ]
    
    try:
        print("Running yt-dlp to fetch video list...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line: continue
            try:
                data = json.loads(line)
                if data.get("id") and data.get("title"):
                    videos.append({"id": data["id"], "title": data["title"]})
            except json.JSONDecodeError:
                pass
        
        print(f"Found {len(videos)} videos. Finding a fresh one...")
        
        # Load History
        history_file = "downloads_history.txt"
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = f.read().splitlines()
        else:
            history = []
            
        # Shuffle to ensure randomness, then pick first non-duplicate
        random.shuffle(videos)
        chosen = None
        for v in videos:
            if v['id'] not in history:
                chosen = v
                break
                
        if not chosen:
            print("Notice: No fresh videos found in the latest 50 list. Try increasing the --playlist-end limit.")
            return None, None
        
        # Save to history immediately
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(chosen['id'] + "\n")
            
        target_v_url = f"https://www.youtube.com/watch?v={chosen['id']}"
        print(f"Selected: {chosen['title']} ({target_v_url})")
        
        # We enforce a generic name 'audio.wav' so downstream scripts don't have to guess
        audio_file = os.path.join(output_dir, "audio.wav")
        
        # If it exists from a previous run, delete it so we don't skip download by mistake
        if os.path.exists(audio_file):
            os.remove(audio_file)
            
        dl_cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "wav", 
            "--output", audio_file,
            target_v_url
        ]
        
        print("Downloading audio (WAV format, this may take a moment)...")
        subprocess.run(dl_cmd, capture_output=True, text=True, check=True)
        
        if os.path.exists(audio_file):
            print(f"Download complete: {audio_file}")
            return audio_file, chosen['title']
        else:
            print("Download failed. Audio file not found.")
            return None, None
            
    except subprocess.CalledProcessError as e:
        print(f"Command Error: yt-dlp failed. Make sure ffmpeg and yt-dlp are installed. error: {e}")
        return None, None
    except Exception as e:
        print(f"Error downloading: {e}")
        return None, None

if __name__ == "__main__":
    audio_path, title = download_random_ncs_song()
    if title:
        print(f"Success! Ready for visualizer: {title}")
