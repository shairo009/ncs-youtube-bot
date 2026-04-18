import os
import random
import subprocess
import sys
from moviepy.editor import AudioFileClip, VideoFileClip

def create_music_video(audio_path="downloads/audio.wav", image_path="downloads/background_hd.jpg", output_path="downloads/final_video.mp4", video_type="long", song_title="NCS Release"):
    if not os.path.exists(audio_path):
        print("Error: Missing audio source.")
        return False
        
    print("Preparing to assemble modern Neumorphic UI...")
    
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
            audio_clip = audio_clip.subclip(time_offset, time_offset + 59)
            duration = 59
            
    # 2. Inject Song Title into HTML Template
    template_path = "ui_template.html"
    if not os.path.exists(template_path):
        print(f"Error: Custom UI template {template_path} not found!")
        return False
        
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
        
    display_title = song_title[:32] + "..." if len(song_title) > 32 else song_title
    html = html.replace("{{SONG_NAME}}", display_title)
    html = html.replace("{{DURATION}}", str(duration))
    
    with open("temp_ui.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    # 3. Call Playwright to record UI locally
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
    video_clip = VideoFileClip(ui_webm_path).subclip(0, duration)
    final_clip = video_clip.set_audio(audio_clip)
    
    try:
        final_clip.write_videofile(
            output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            threads=2,
            preset="ultrafast",
            logger=None
        )
        print(f"Success! Final video rendered at: {output_path}")
        return output_path
    except Exception as e:
        print(f"Failed to render video: {e}")
        return False
