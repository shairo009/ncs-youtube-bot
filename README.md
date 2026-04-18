# 🎵 NCS YouTube Bot — Fully Automated Channel 🚀

This is a professional, AI-powered automation pipeline designed to run a YouTube channel featuring **NoCopyrightSounds (NCS)** music. It leverages AI image generation, sophisticated audio processing, and automated uploading to maintain a high-frequency posting schedule (Shorts & Long videos).

## 🌟 Features

- **Automated Music Sourcing**: Automatically fetches tracks from the official NCS YouTube channel using `yt-dlp`.
- **AI Background Visuals**: Generates aesthetic, theme-based backgrounds using **Pollinations AI**.
- **HD Upscaling**: Uses a local **ESPCN/EDSR OpenCV DNN super-resolution model** to upscale images to high definition.
- **Dynamic Beat-Visualizer**: Sleek "Monstercat-style" bottom bar equalizer that reacts to the music's frequency.
- **Smart Scheduling**: 
  - **Shorts**: 5 staggered posts per day with automatic 59-second audio cropping from the track's climax.
  - **Long Videos**: 1 full-length track upload daily.
- **CI/CD Deployment**: Fully integrated with **GitHub Actions** for 24/7 serverless operation.

## 🛠️ Project Structure

- `main.py`: The orchestrator that coordinates the download, generation, and upload phases.
- `downloader.py`: Handles high-quality audio extraction.
- `image_gen.py`: Manages AI prompt engineering and resolution scaling (9:16 for Shorts / 16:9 for Long).
- `video_compiler.py`: The rendering engine that merges audio, static visuals, and the dynamic equalizer.
- `uploader.py`: YouTube API v3 integration for publishing.
- `.github/workflows/ncs_pipeline.yml`: The automation engine that triggers runs throughout the day.

## 🚀 Getting Started

### 0. Track Source Setup (Legal Mode, No Cookies)
This bot now uses a legal source file instead of scraping YouTube.

1. Open `ncs_tracks.txt`.
2. Paste **direct official NCS audio download links** (`.mp3/.wav/.flac`), one per line.
3. Save the file and run the pipeline.

If `ncs_tracks.txt` is empty (or contains non-direct links like `https://ncs.io/...`), the run will stop safely before video generation.

### 1. Local Authentication (One-time)
Before deploying to GitHub, you must bind your channel:
1. Place your `client_secret.json` in the root directory.
2. Run `python main.py --type short`.
3. Complete the Google OAuth flow in your browser. This will create a `token.json` file.

### 2. GitHub Deployment
1. Create a **Public** repository and push this code.
2. Go to **Settings > Secrets and variables > Actions**.
3. Create two Secrets:
   - `CLIENT_SECRET_JSON`: Copy content from `client_secret.json`.
   - `TOKEN_JSON`: Copy content from `token.json`.

## ⚠️ Requirements

- Python 3.10+
- FFmpeg (Installed on system)
- OpenCV, MoviePy, Librosa, Pydub, and Google API Client.

---
*Built with ❤️ for automated content creators.*
