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


def compute_spectrum_data(audio_path, duration, offset=0.0, samples_per_sec=10, n_bands=7):
    """
    Compute per-frequency-band amplitude data for the spectrum visualizer.
    Returns list of frames: [[band1, band2, ..., band7], ...] each 0-100.
    7 bands: sub-bass, bass, low-mid, mid, high-mid, high, air
    """
    # Frequency band edges (Hz)
    BAND_EDGES = [20, 60, 250, 500, 2000, 4000, 8000, 20000]

    try:
        import librosa

        y, sr = librosa.load(audio_path, sr=None, mono=True, offset=offset, duration=duration)
        hop_length = max(1, int(sr / samples_per_sec))

        # Full STFT
        D = np.abs(librosa.stft(y, hop_length=hop_length, n_fft=2048))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
        n_frames = D.shape[1]

        # Compute energy per band per frame
        raw_bands = []
        for b in range(n_bands):
            low_hz = BAND_EDGES[b]
            high_hz = BAND_EDGES[b + 1]
            mask = (freqs >= low_hz) & (freqs < high_hz)
            if not np.any(mask):
                raw_bands.append(np.zeros(n_frames))
                continue
            energy = D[mask, :].mean(axis=0)  # mean energy across bins in band
            raw_bands.append(energy)

        # Normalise each band independently (0-100)
        norm_bands = []
        for energy in raw_bands:
            peak = energy.max() if energy.max() > 0 else 1.0
            norm_bands.append((energy / peak * 100).tolist())

        # Transpose to (n_frames, n_bands), trim/pad to target length
        target_len = int(duration * samples_per_sec)
        result = []
        for fi in range(target_len):
            if fi < n_frames:
                frame = [max(12.0, norm_bands[b][fi]) for b in range(n_bands)]
            else:
                frame = [12.0] * n_bands
            result.append(frame)

        print(f"  Spectrum data: {len(result)} frames x {n_bands} bands.")
        return result

    except Exception as e:
        print(f"  Warning: spectrum compute failed ({e}). Using animated fallback.")
        target_len = int(duration * samples_per_sec)
        return [
            [max(12.0, 40 + 40 * abs(np.sin(fi * 0.3 + b * 0.9)))
             for b in range(n_bands)]
            for fi in range(target_len)
        ]


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

    print(f"Preparing Neumorphic UI for genre: {song_genre}...")

    # 1. Snippet the Audio
    audio_clip = AudioFileClip(audio_path)
    time_offset = 0.0
    duration = audio_clip.duration

    if video_type == "short":
        if duration > 60:
            time_offset = random.uniform(duration * 0.3, duration * 0.6)
            if time_offset + 59 > duration:
                time_offset = duration - 59
            print(f"Snipping 59s from {time_offset:.1f}s")
            audio_clip = audio_clip.subclip(time_offset, time_offset + 59)
            duration = 59

    # 2. Compute per-band spectrum data
    print("Computing spectrum data for beat-sync visualizer...")
    spectrum_data = compute_spectrum_data(audio_path, duration, offset=time_offset)

    # 3. Inject ALL placeholders into HTML Template
    template_path = "ui_template.html"
    if not os.path.exists(template_path):
        print(f"Error: {template_path} not found!")
        return False

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

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
    html = html.replace("{{AMPLITUDE_DATA}}", json.dumps(spectrum_data))

    with open("temp_ui.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML ready: '{display_title}' | {theme_color} | {len(spectrum_data)} frames")

    # 4. Playwright record
    ui_webm_path = "downloads/ui_recording.webm"
    print(f"Playwright recording for {duration}s...")
    try:
        subprocess.run(
            [sys.executable, "html_recorder.py", str(duration), ui_webm_path],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Playwright failed: {e}")
        return False

    if not os.path.exists(ui_webm_path):
        print("Error: WebM not created.")
        return False

    # 5. Mux video + audio
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
        print(f"Done! Video at: {output_path}")
        return output_path
    except Exception as e:
        print(f"Render failed: {e}")
        return False
