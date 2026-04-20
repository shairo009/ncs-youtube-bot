import os
import subprocess
import requests


def fetch_board_gif(game_id: str) -> str:
    path = f"downloads/board_{game_id}.gif"
    url = f"https://lichess.org/game/export/gif/{game_id}.gif?theme=brown&piece=cburnett"
    r = requests.get(url, timeout=15)
    if r.status_code == 200:
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    raise Exception(f"Board GIF fetch failed: {r.status_code}")


def gif_to_mp4(gif_path: str, out: str) -> str:
    subprocess.run([
        "ffmpeg", "-y", "-i", gif_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-movflags", "faststart", "-pix_fmt", "yuv420p", out
    ], check=True, capture_output=True)
    return out


def add_effects(input_path: str, out: str) -> str:
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-vf", (
            "zoompan=z='if(gte(t,5),min(zoom+0.002,1.5),1)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
            "drawbox=x=220:y=220:w=130:h=130:color=red@0.8:t=5,"
            "drawtext=text='BLUNDER!':fontcolor=red:fontsize=40:x=220:y=365:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ),
        "-c:a", "copy", out
    ], check=True, capture_output=True)
    return out


def merge_audio(video: str, audio: str, out: str) -> str:
    subprocess.run([
        "ffmpeg", "-y", "-i", video, "-i", audio,
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", "-c:v", "copy", out
    ], check=True, capture_output=True)
    return out


def trim(input_path: str, out: str, duration: int = 10) -> str:
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-t", str(duration), "-c", "copy", out
    ], check=True, capture_output=True)
    return out


def create_video(game_id: str, blunder_index: int, voice_file: str, output_path: str) -> str:
    os.makedirs("downloads", exist_ok=True)

    gif = fetch_board_gif(game_id)
    raw = f"downloads/raw_{game_id}.mp4"
    gif_to_mp4(gif, raw)

    trimmed = f"downloads/trimmed_{game_id}.mp4"
    trim(raw, trimmed, 10)

    effects = f"downloads/effects_{game_id}.mp4"
    add_effects(trimmed, effects)

    merge_audio(effects, voice_file, output_path)
    print(f"Video ready: {output_path}")
    return output_path
