import os
import random
import subprocess
import sys
import json
import numpy as np
from pathlib import Path
from moviepy.editor import AudioFileClip, VideoFileClip

def get_ncs_color(genre):
    mapping = {
        "Drum & Bass": "#F44336",
        "Drumstep": "#F44336",
        "House": "#FFC107",
        "Bass House": "#FFC107",
        "Trap": "#4CAF50",
        "Future Bass": "#4CAF50",
        "Electro": "#FF9800",
        "Electronic": "#FF9800",
        "Dubstep": "#2196F3",
        "Future House": "#9C27B0",
        "Indie": "#1DE9B6",
        "Alternative": "#1DE9B6",
        "Chillstep": "#00BCD4",
        "Hardstyle": "#FFFFFF",
    }
    for g, color in mapping.items():
        if g.lower() in genre.lower():
            return color
    return "#00BCD4"


def compute_amplitude_data(audio_path, duration, offset=0.0, samples_per_sec=10):
    """
    Compute amplitude envelope from audio at `samples_per_sec` Hz.
    Returns a flat list of floats (0-100 range) for the JS visualizer.
    """
    try:
        import librosa
        y, sr = librosa.load(audio_path, sr=None, mono=True, offset=offset, duration=duration)
        hop_length = max(1, int(sr / samples_per_sec))
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

        rms_max = rms.max() if rms.max() > 0 else 1.0
        normalised = (rms / rms_max * 100).tolist()

        target_len = int(duration * samples_per_sec)
        if len(normalised) > target_len:
            normalised = normalised[:target_len]
        else:
            normalised += [normalised[-1] if normalised else 40.0] * (target_len - len(normalised))

        print(f"  Amplitude data: {len(normalised)} samples computed.")
        return normalised

    except Exception as e:
        print(f"  Warning: Could not compute amplitude data ({e}). Using sine fallback.")
        target_len = int(duration * samples_per_sec)
        return [40 + 40 * abs(np.sin(i * 0.3)) for i in range(target_len)]


def create_music_video(
    audio_path="downloads/audio.wav",
    image_path=None,
    output_path="downloads/final_video.mp4",
    video_type="long",
    song_title="NCS Release",
    song_genre="NCS Release",
):
    if not os.path.exists(audio_path):
        print("Error: Missing audio source.")
        return False

    print(f"Preparing to assemble modern Neumorphic UI for genre: {song_genre}...")

    # 1. Snippet the Audio
    audio_clip = AudioFileClip(audio_path)
    time_offset = 0.0
    duration = audio_clip.duration

    if video_type == "short":
        if duration > 60:
            time_offset = random.uniform(duration * 0.3, duration * 0.6)
            if time_offset + 59 > duration:
                time_offset = duration - 59
            print(f"Snipping 59s track from {time_offset:.1f}s")
            audio_clip = audio_clip.subclip(time_offset, time_offset + 59)
            duration = 59

    # 2. Compute Amplitude Data for the visualizer (FIX: this was missing before)
    print("Computing amplitude data for visualizer...")
    amplitude_data = compute_amplitude_data(audio_path, duration, offset=time_offset)

    # 3. Inject ALL placeholders into HTML Template
    template_path = "ui_template.html"
    if not os.path.exists(template_path):
        print(f"Error: Custom UI template {template_path} not found!")
        return False

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Sanitise title
    display_title = song_title[:32] + "..." if len(song_title) > 32 else song_title
    display_title = (
        display_title
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    theme_color = get_ncs_color(song_genre)

    html = html.replace("{{SONG_NAME}}", display_title)
    html = html.replace("{{DURATION}}", str(duration))
    html = html.replace("{{THEME_COLOR}}", theme_color)
    html = html.replace("{{AMPLITUDE_DATA}}", json.dumps(amplitude_data))  # FIX: was never replaced before

    with open("temp_ui.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML template ready: song='{display_title}', color={theme_color}, amp_samples={len(amplitude_data)}")

    # 4. Call Playwright to record UI
    ui_webm_path = "downloads/ui_recording.webm"
    print(f"Running Playwright Recorder for {duration} seconds...")
    try:
        subprocess.run(
            [sys.executable, "html_recorder.py", str(duration), ui_webm_path],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Playwright recording failed: {e}")
        return False

    # 5. Mix Video and Audio using MoviePy
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
            audio_bitrate="320k",
            threads=2,
            preset="ultrafast",
            logger=None,
        )
        print(f"Success! Final video rendered at: {output_path}")
        return output_path
    except Exception as e:
        print(f"Failed to render video: {e}")
        return False
