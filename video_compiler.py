import os
import random
import subprocess
import sys
import json
import re
import numpy as np
from pathlib import Path
from moviepy.editor import AudioFileClip, VideoFileClip


# ────────────────────────────────────────────────────────
# NCS Official Genre → Brand Color Mapping
# ────────────────────────────────────────────────────────
NCS_GENRE_COLORS = {
    # Drum & Bass family → Red
    "drum & bass":        "#E53935",
    "drum and bass":      "#E53935",
    "drum n bass":        "#E53935",
    "drum bass":          "#E53935",
    "d&b":                "#E53935",
    "dnb":                "#E53935",
    "drumstep":           "#E53935",
    "liquid dnb":         "#29B6F6",
    "liquid drum":        "#29B6F6",
    "neurofunk":          "#B71C1C",
    "jungle":             "#E53935",
    "breakbeat":          "#EF5350",
    "breaks":             "#EF5350",

    # House family → Yellow / Orange
    "rally house":        "#FDD835",
    "slap house":         "#FDD835",
    "melodic house":      "#FDD835",
    "speed house":        "#FF6F00",
    "afro house":         "#FFB300",
    "house":              "#FDD835",
    "bass house":         "#FB8C00",
    "future house":       "#FF6F00",
    "progressive house":  "#F57C00",
    "deep house":         "#FFB300",
    "tech house":         "#FF8F00",
    "tropical house":     "#FFCA28",
    "big room":           "#FF8F00",

    # Trap / Hip Hop family → Green
    "hybrid trap":        "#43A047",
    "jersey club":        "#43A047",
    "trap":               "#43A047",
    "future trap":        "#2E7D32",
    "hip hop":            "#388E3C",
    "phonk":              "#558B2F",
    "footwork":           "#33691E",
    "r&b":                "#EC407A",
    "rnb":                "#EC407A",
    "funk":               "#FF7043",
    "soul":               "#FF7043",

    # Future Bass / Melodic → Teal / Cyan
    "future bass":        "#00ACC1",
    "melodic dubstep":    "#00897B",
    "chillstep":          "#29B6F6",
    "chill":              "#4FC3F7",
    "midtempo":           "#00BCD4",
    "bass":               "#00ACC1",

    # Dubstep → Blue
    "dubstep":            "#1E88E5",
    "complextro":         "#1565C0",

    # Electronic / Electro / EDM → Orange
    "electronic":         "#FB8C00",
    "electro":            "#F57C00",
    "edm":                "#FB8C00",
    "dance":              "#FF7043",

    # Trance → Purple
    "trance":             "#AB47BC",
    "psytrance":          "#7B1FA2",
    "uplifting trance":   "#AB47BC",
    "progressive trance": "#9C27B0",

    # Indie / Alternative / Pop → Warm Coral / Pink
    "indie":              "#FF7043",
    "alternative":        "#FF5722",
    "pop":                "#EC407A",
    "rock":               "#FF5722",
    "punk":               "#FF1744",
    "metal":              "#90A4AE",
    "acoustic":           "#8D6E63",
    "folk":               "#8D6E63",

    # Ambient / Orchestral → Indigo
    "ambient":            "#5C6BC0",
    "orchestral":         "#3949AB",
    "classical":          "#3F51B5",
    "jazz":               "#5C6BC0",
    "piano":              "#5C6BC0",
    "acoustic piano":     "#5C6BC0",

    # Hardstyle → Silver/Grey
    "hardstyle":          "#B0BEC5",
    "hardcore":           "#90A4AE",
    "rawstyle":           "#78909C",
    "frenchcore":         "#90A4AE",

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
    "chillwave":          "#BA68C8",
    "dreamwave":          "#CE93D8",

    # Glitch / Experimental → Lime Green
    "glitch":             "#C6FF00",
    "experimental":       "#76FF03",
    "noise":              "#C6FF00",

    # Rave / Party → Hot Pink
    "rave":               "#FF1744",
    "party":              "#FF4081",
    "festival":           "#FF4081",

    # Default NCS Brand Cyan
    "ncs release":        "#00E5FF",
}

# Keyword-based fallback (when genre title contains hints)
KEYWORD_COLORS = [
    # DnB / Drum & Bass
    (["drum & bass", "drum n bass", "neurofunk", "liquid dnb", "liquid drum"], "#E53935"),
    (["dnb", "d&b", "drumstep", "jungle", "breakbeat", "breaks"],             "#E53935"),
    (["drum", "bass"],                                                          "#E53935"),

    # House (check specific before generic)
    (["rally house", "slap house", "melodic house", "afro house"],             "#FDD835"),
    (["speed house", "future house", "big room"],                              "#FF6F00"),
    (["bass house"],                                                            "#FB8C00"),
    (["tech house", "deep house"],                                              "#FF8F00"),
    (["tropical house"],                                                        "#FFCA28"),
    (["house"],                                                                 "#FDD835"),

    # Trap / Hip Hop
    (["hybrid trap", "jersey club", "footwork"],                               "#43A047"),
    (["trap", "hip hop", "phonk"],                                              "#43A047"),

    # Trance
    (["trance", "psy", "uplifting", "psytrance"],                              "#AB47BC"),

    # Future Bass / Melodic / Midtempo
    (["future bass", "melodic dubstep", "midtempo"],                           "#00ACC1"),
    (["melodic"],                                                               "#00ACC1"),

    # Dubstep / Complextro
    (["dubstep", "complextro"],                                                 "#1E88E5"),

    # Chill / Ambient / Lo-fi
    (["chillstep", "chill", "lofi", "lo-fi", "ambient", "sleep", "piano"],    "#29B6F6"),
    (["chillwave", "dreamwave"],                                                "#BA68C8"),

    # Synthwave / Retrowave
    (["synthwave", "retrowave", "outrun", "vaporwave", "synth"],               "#E91E63"),
    (["neon", "cyber", "retro", "wave"],                                        "#E91E63"),

    # Electronic / EDM / Dance
    (["electro", "electronic", "edm", "dance"],                                "#FB8C00"),

    # Hardstyle / Hardcore
    (["hardstyle", "hardcore", "rawstyle", "frenchcore"],                      "#B0BEC5"),

    # Dark / Gothic / Witch
    (["witch", "dark", "gothic", "shadow", "haunted", "cursed", "occult"],    "#9C27B0"),
    (["horror", "luster"],                                                      "#9C27B0"),

    # Glitch / Experimental
    (["glitch", "experiment", "noise"],                                         "#C6FF00"),

    # Indie / Alt / Pop / R&B
    (["r&b", "rnb", "soul", "funk"],                                            "#EC407A"),
    (["indie", "alternative", "rock", "punk"],                                  "#FF7043"),
    (["pop"],                                                                    "#EC407A"),

    # Orchestral / Classical
    (["orchestral", "classical", "jazz", "acoustic"],                           "#3949AB"),
]


def _normalize_color_text(value):
    value = (value or "").lower().replace("｜", "|")
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\bd\s*n\s*b\b", "dnb", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def get_ncs_color(genre, song_title=""):
    """
    Return the NCS brand color for a genre.
    Uses normalized matching so NCS label variations like DnB, Drum and Bass,
    Drum & Bass, and bracketed title hints still resolve to the right color.
    """
    genre_norm = _normalize_color_text(genre)
    title_norm = _normalize_color_text(song_title)
    combined_norm = f"{genre_norm} {title_norm}".strip()

    # Direct genre match. Check longest labels first so specific styles like
    # "bass house" and "liquid dnb" are not swallowed by generic "house"/"dnb".
    for key in sorted(NCS_GENRE_COLORS, key=len, reverse=True):
        if key == "ncs release":
            continue
        key_norm = _normalize_color_text(key)
        if key_norm and key_norm in genre_norm:
            return NCS_GENRE_COLORS[key]

    # Keyword fallback on both genre and title.
    for keywords, color in KEYWORD_COLORS:
        normalized_keywords = [_normalize_color_text(kw) for kw in keywords]
        if normalized_keywords == ["drum", "bass"]:
            if all(kw in combined_norm for kw in normalized_keywords):
                return color
        elif any(kw and kw in combined_norm for kw in normalized_keywords):
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
