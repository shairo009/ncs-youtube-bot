import os
import random
import subprocess
import sys
import json
import numpy as np
from pathlib import Path
from moviepy.editor import AudioFileClip, VideoFileClip


# ────────────────────────────────────────────────────────
# NCS Official Genre → Brand Color Mapping
# ────────────────────────────────────────────────────────
NCS_GENRE_COLORS = {
    # Drum & Bass family  → Red
    "drum & bass":        "#E53935",
    "dnb":                "#E53935",
    "drumstep":           "#E53935",
    "liquid dnb":         "#E53935",

    # House family → Yellow / Orange
    "house":              "#FDD835",
    "bass house":         "#FB8C00",
    "future house":       "#FF6F00",
    "progressive house":  "#F57C00",
    "deep house":         "#FFB300",
    "tech house":         "#FF8F00",
    "tropical house":     "#FFCA28",

    # Trap family → Green
    "trap":               "#43A047",
    "future trap":        "#2E7D32",
    "hip hop":            "#388E3C",
    "phonk":              "#558B2F",

    # Future Bass / Melodic → Teal / Cyan
    "future bass":        "#00ACC1",
    "melodic dubstep":    "#00897B",
    "chillstep":          "#29B6F6",
    "chill":              "#4FC3F7",

    # Dubstep → Blue
    "dubstep":            "#1E88E5",
    "complextro":         "#1565C0",

    # Electronic / Electro → Orange
    "electronic":         "#FB8C00",
    "electro":            "#F57C00",

    # Indie / Alternative → Warm Coral
    "indie":              "#FF7043",
    "alternative":        "#FF5722",
    "pop":                "#EC407A",

    # Ambient / Orchestral → Indigo
    "ambient":            "#5C6BC0",
    "orchestral":         "#3949AB",
    "classical":          "#3F51B5",

    # Hardstyle → Silver/White
    "hardstyle":          "#B0BEC5",
    "hardcore":           "#90A4AE",

    # Witch House / Dark / Gothic → Deep Purple/Violet
    "witch house":        "#9C27B0",
    "dark":               "#7B1FA2",
    "gothic":             "#6A1B9A",
    "darkwave":           "#8E24AA",
    "horror":             "#4A148C",
    "occult":             "#6A1B9A",

    # Synthwave / Retrowave → Pink/Magenta
    "synthwave":          "#E91E63",
    "retrowave":          "#F06292",
    "outrun":             "#FF4081",
    "vaporwave":          "#CE93D8",
    "lo-fi":              "#BA68C8",
    "lofi":               "#BA68C8",

    # Glitch / Experimental → Lime Green
    "glitch":             "#C6FF00",
    "experimental":       "#76FF03",

    # Rave / Party → Hot Pink
    "rave":               "#FF1744",
    "party":              "#FF4081",

    # Default NCS Brand Cyan
    "ncs release":        "#00E5FF",
}

# Keyword-based fallback (when genre = "NCS Release" but title has hints)
KEYWORD_COLORS = [
    (["drum", "bass", "dnb"],                         "#E53935"),
    (["trap", "hip hop", "phonk"],                    "#43A047"),
    (["house", "tropical"],                           "#FDD835"),
    (["dubstep", "drum bass"],                        "#1E88E5"),
    (["future bass", "melodic"],                      "#00ACC1"),
    (["chill", "ambient", "sleep"],                   "#29B6F6"),
    (["electro", "electronic"],                       "#FB8C00"),
    (["indie", "alternative", "pop"],                 "#FF7043"),
    (["hardstyle", "hardcore"],                       "#B0BEC5"),
    (["witch", "dark", "gothic", "shadow", "luster", "haunted", "cursed"], "#9C27B0"),
    (["synth", "retro", "wave", "neon", "cyber"],     "#E91E63"),
    (["glitch", "experiment"],                        "#C6FF00"),
]


def get_ncs_color(genre, song_title=""):
    """
    Return the NCS brand color for a genre.
    Falls back to keyword detection on song title if genre is generic.
    """
    genre_lower = genre.lower().strip()

    # Direct genre match — skip "ncs release" so keyword fallback gets a chance
    for key, color in NCS_GENRE_COLORS.items():
        if key == "ncs release":
            continue
        if key in genre_lower:
            return color

    # Keyword fallback on title (runs for all genres including "NCS Release")
    title_lower = song_title.lower()
    for keywords, color in KEYWORD_COLORS:
        if any(kw in title_lower for kw in keywords):
            return color

    # Default NCS cyan (true last resort)
    return "#00E5FF"


# ────────────────────────────────────────────────────────
# Spectrum Data
# ────────────────────────────────────────────────────────
def compute_spectrum_data(audio_path, duration, offset=0.0, samples_per_sec=10, n_bands=7):
    """
    Compute per-frequency-band amplitude data.
    Returns [[b1..b7], ...] per frame, each value 0-100.
    7 bands: sub-bass, bass, low-mid, mid, high-mid, high, air
    """
    BAND_EDGES = [20, 60, 250, 500, 2000, 4000, 8000, 20000]

    try:
        import librosa
        y, sr = librosa.load(audio_path, sr=None, mono=True, offset=offset, duration=duration)
        hop_length = max(1, int(sr / samples_per_sec))
        D = np.abs(librosa.stft(y, hop_length=hop_length, n_fft=2048))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
        n_frames = D.shape[1]

        raw_bands = []
        for b in range(n_bands):
            mask = (freqs >= BAND_EDGES[b]) & (freqs < BAND_EDGES[b + 1])
            if not np.any(mask):
                raw_bands.append(np.zeros(n_frames))
                continue
            raw_bands.append(D[mask, :].mean(axis=0))

        norm_bands = []
        for energy in raw_bands:
            peak = energy.max() if energy.max() > 0 else 1.0
            norm_bands.append((energy / peak * 100).tolist())

        target_len = int(duration * samples_per_sec)
        result = []
        for fi in range(target_len):
            if fi < n_frames:
                result.append([max(12.0, norm_bands[b][fi]) for b in range(n_bands)])
            else:
                result.append([12.0] * n_bands)

        print(f"  Spectrum data: {len(result)} frames x {n_bands} bands.")
        return result

    except Exception as e:
        print(f"  Warning: spectrum compute failed ({e}). Using fallback.")
        target_len = int(duration * samples_per_sec)
        return [
            [max(12.0, 40 + 40 * abs(np.sin(fi * 0.3 + b * 0.9)))
             for b in range(n_bands)]
            for fi in range(target_len)
        ]


# ────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────
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

    # Pick theme color using genre + song title for best match
    theme_color = get_ncs_color(song_genre, song_title)
    print(f"Genre: {song_genre} → Theme color: {theme_color}")

    # 1. Snippet audio
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

    # 2. Compute spectrum data
    print("Computing spectrum data...")
    spectrum_data = compute_spectrum_data(audio_path, duration, offset=time_offset)

    # 3. Inject placeholders
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

    html = html.replace("{{SONG_NAME}}", display_title)
    html = html.replace("{{DURATION}}", str(duration))
    html = html.replace("{{THEME_COLOR}}", theme_color)
    html = html.replace("{{AMPLITUDE_DATA}}", json.dumps(spectrum_data))

    with open("temp_ui.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML ready: '{display_title}' | color={theme_color}")

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

    # 5. Mux
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
