import os
import random
import subprocess
import sys
from pathlib import Path
from moviepy import AudioFileClip, VideoFileClip
import librosa
import numpy as np
import json

def get_ncs_color(genre):
    # Official-ish NCS Color Mapping
    mapping = {
        "Drum & Bass": "#F44336", # Red
        "DnB": "#F44336",
        "Drumstep": "#F44336",
        "House": "#FFC107",        # Yellow
        "Bass House": "#FFC107",
        "Trap": "#4CAF50",         # Green
        "Future Bass": "#4CAF50",
        "Electro": "#FF9800",      # Orange
        "Electronic": "#FF9800",
        "Dubstep": "#2196F3",      # Blue
        "Future House": "#9C27B0", # Purple
        "Indie": "#1DE9B6",        # Mint
        "Alternative": "#1DE9B6",
        "Chillstep": "#00BCD4",    # Cyan
        "Hardstyle": "#FFFFFF",    # White
    }
    for g, color in mapping.items():
        if g.lower() in genre.lower():
            return color
    return "#00BCD4" # Default Cyan

def get_audio_amplitude(audio_path, start_time, duration, fps=10):
    """
    Analyzes audio and returns a list of normalized amplitude values (0-100).
    """
    try:
        print(f"📊 Analyzing audio for beat sync ({duration:.1f}s)...")
        # Load only the required part
        y, sr = librosa.load(audio_path, offset=start_time, duration=duration)
        
        # Calculate RMS amplitude
        hop_length = int(sr / fps)
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        
        # Normalize to 0-1.0
        if len(rms) > 0:
            rms_min = np.min(rms)
            rms_max = np.max(rms)
            if rms_max > rms_min:
                rms = (rms - rms_min) / (rms_max - rms_min)
            
            # Map to 20-100 for height percentage
            rms_final = (rms * 80 + 20).astype(int).tolist()
            return rms_final
    except Exception as e:
        print(f"⚠️ Audio analysis failed: {e}")
    return []

def create_music_video(audio_path="downloads/audio.wav", image_path=None, output_path="downloads/final_video.mp4", video_type="long", song_title="NCS Release", song_genre="NCS Release"):
    if not os.path.exists(audio_path):
        print("Error: Missing audio source.")
        return False
        
    print(f"Preparing to assemble modern Neumorphic UI for genre: {song_genre}...")
    
    # 1. Snippet the Audio
    audio_clip = AudioFileClip(audio_path)
    time_offset = 0
    duration = audio_clip.duration
    
    if video_type == "short":
        if duration > 60:
            time_offset = random.uniform(duration * 0.3, duration * 0.6)
            if time_offset + 59 > duration:
                time_offset = duration - 59
            print(f"✂️  Snipping 59s track from {time_offset:.1f}s")
            audio_clip = audio_clip.subclipped(time_offset, time_offset + 59)
            duration = 59
            
    # 2. Analyze Audio for Visualizer Data
    amplitude_data = get_audio_amplitude(audio_path, time_offset, duration, fps=10)
    
    # 3. Inject Data into HTML Template
    template_path = "ui_template.html"
    if not os.path.exists(template_path):
        print(f"Error: Custom UI template {template_path} not found!")
        return False
        
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
        
    display_title = song_title[:32] + "..." if len(song_title) > 32 else song_title
    theme_color = get_ncs_color(song_genre)
    
    html = html.replace("{{SONG_NAME}}", display_title)
    html = html.replace("{{DURATION}}", str(duration))
    html = html.replace("{{THEME_COLOR}}", theme_color)
    html = html.replace("{{AMPLITUDE_DATA}}", json.dumps(amplitude_data))
    
    with open("temp_ui.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    # 4. Call Playwright to record UI locally
    ui_webm_path = "downloads/ui_recording.webm"
    print(f"Running Playwright Recorder for {duration} seconds...")
    try:
        subprocess.run([sys.executable, "html_recorder.py", str(duration), ui_webm_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Playwright recording failed: {e}")
        return False
        
    # 4. Mix Video and Audio using MoviePy
    if not os.path.exists(ui_webm_path):
        print("Error: WebM UI video was not created by Playwright.")
        return False
        
    print("Muxing final MP4...")
    video_clip = VideoFileClip(ui_webm_path).subclipped(0, duration)
    final_clip = video_clip.with_audio(audio_clip)
    
    try:
        final_clip.write_videofile(
            output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            audio_bitrate="320k", # Force High Quality Audio
            threads=2,
            preset="ultrafast",
            logger=None
        )
        print(f"Success! Final video rendered at: {output_path}")
        return output_path
    except Exception as e:
        print(f"Failed to render video: {e}")
        return False
