import subprocess
import random
import os
import json
import requests
from urllib.parse import urlparse

MIN_AUDIO_BITRATE_KBPS = 256
MIN_SAMPLE_RATE_HZ = 44100

def _load_track_urls(track_list_file="ncs_tracks.txt"):
    if not os.path.exists(track_list_file):
        return []

    urls = []
    with open(track_list_file, "r", encoding="utf-8") as f:
        for line in f:
            item = line.strip()
            if not item or item.startswith("#"):
                continue
            urls.append(item)
    return urls


def _is_supported_direct_audio_url(url):
    path = urlparse(url).path.lower()
    return path.endswith(".mp3") or path.endswith(".wav") or path.endswith(".flac")


def _pick_fresh_track(urls, history_file="downloads_history.txt"):
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            history = set(f.read().splitlines())
    else:
        history = set()

    random.shuffle(urls)
    for url in urls:
        if url not in history:
            return url
    return None


def _save_history(selected_url, history_file="downloads_history.txt"):
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(selected_url + "\n")


def _download_direct_audio(url, out_mp3):
    with requests.get(url, stream=True, timeout=90) as r:
        r.raise_for_status()
        with open(out_mp3, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


def _convert_to_wav(src_audio, target_wav):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            src_audio,
            "-acodec",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            target_wav,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _probe_audio_quality(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    info = json.loads(result.stdout)
    streams = info.get("streams", [])
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    sample_rate = int(audio_stream.get("sample_rate") or 0)
    bit_rate_raw = (
        audio_stream.get("bit_rate")
        or info.get("format", {}).get("bit_rate")
        or 0
    )
    bit_rate_kbps = int(bit_rate_raw) / 1000 if bit_rate_raw else 0
    return sample_rate, bit_rate_kbps


def _is_high_quality(sample_rate, bit_rate_kbps):
    # For lossless sources where bitrate may be unavailable, rely on sample rate.
    if bit_rate_kbps <= 0 and sample_rate >= MIN_SAMPLE_RATE_HZ:
        return True
    return sample_rate >= MIN_SAMPLE_RATE_HZ and bit_rate_kbps >= MIN_AUDIO_BITRATE_KBPS


def download_random_ncs_song(output_dir="downloads"):
    """
    Legal/offical-link mode:
    - Reads direct NCS audio download URLs from ncs_tracks.txt
    - Downloads one fresh track
    - Converts to downloads/audio.wav
    """
    os.makedirs(output_dir, exist_ok=True)

    track_urls = _load_track_urls("ncs_tracks.txt")
    if not track_urls:
        print("No track URLs found in ncs_tracks.txt")
        print("Add direct NCS download URLs (mp3/wav/flac), one per line.")
        return None, None

    valid_urls = [u for u in track_urls if _is_supported_direct_audio_url(u)]
    if not valid_urls:
        print("No direct audio URLs detected in ncs_tracks.txt")
        print("Use direct file links from official NCS download button (ending in .mp3/.wav/.flac).")
        return None, None

    selected_url = _pick_fresh_track(valid_urls)
    if not selected_url:
        print("No fresh track found (all URLs already used in history).")
        return None, None
    candidates = [selected_url] + [u for u in valid_urls if u != selected_url]

    output_wav = os.path.join(output_dir, "audio.wav")
    if os.path.exists(output_wav):
        os.remove(output_wav)

    for candidate_url in candidates:
        print(f"Trying official track URL: {candidate_url}")
        temp_audio = os.path.join(output_dir, "source_audio.tmp")
        if os.path.exists(temp_audio):
            os.remove(temp_audio)

        try:
            _download_direct_audio(candidate_url, temp_audio)
            sample_rate, bit_rate_kbps = _probe_audio_quality(temp_audio)
            print(f"Detected source quality: {sample_rate} Hz, {bit_rate_kbps:.1f} kbps")
            if not _is_high_quality(sample_rate, bit_rate_kbps):
                print("Skipping: source quality below high-quality threshold.")
                continue

            _convert_to_wav(temp_audio, output_wav)
            _save_history(candidate_url)
            title = os.path.basename(urlparse(candidate_url).path) or "NCS Track"
            print(f"Download complete: {output_wav}")
            return output_wav, title
        except requests.RequestException as e:
            print(f"Download request failed: {e}")
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg/FFprobe failed: {e}")
            if getattr(e, "stderr", None):
                print(e.stderr)
        except Exception as e:
            print(f"Unexpected download error: {e}")
        finally:
            if os.path.exists(temp_audio):
                os.remove(temp_audio)

    print("No high-quality track found from provided URLs.")
    return None, None

if __name__ == "__main__":
    audio_path, title = download_random_ncs_song()
    if title:
        print(f"Success! Ready for visualizer: {title}")
