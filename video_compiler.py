import numpy as np
import librosa
from moviepy.editor import AudioFileClip, VideoClip
import cv2
import os
import random

def create_music_video(audio_path="downloads/audio.wav", image_path="downloads/background_hd.jpg", output_path="downloads/final_video.mp4", video_type="long"):
    """
    Creates the final MP4 by generating a dynamic audio visualizer overlay
    and rendering it on top of the HD background along with the audio track.
    Adjusts crop and length based on whether it is 'short' or 'long'.
    """
    if not os.path.exists(audio_path) or not os.path.exists(image_path):
        print("Error: Missing audio or video background sources.")
        return False
        
    print("Loading audio data for visualizer analysis...")
    # Load audio data. We resample to 22050 for faster analysis
    y, sr = librosa.load(audio_path, sr=22050)
    
    print("Generating Beat/Spectrogram data...")
    # Generate Mel spectrogram (extracts frequency bars over time)
    # n_mels determines the number of visual bouncy bars
    num_bars = 60
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=2048, hop_length=512, n_mels=num_bars)
    
    # Convert to Decibels for a more linear audio representation
    S_db = librosa.power_to_db(S, ref=np.max)
    
    # Normalize values between 0.0 and 1.0 so we can scale bar sizes
    min_val = np.min(S_db)
    max_val = np.max(S_db)
    S_normalized = (S_db - min_val) / ((max_val - min_val) + 1e-6)

    print(f"Loading HD background image: {image_path}")
    bg_img = cv2.imread(image_path)
    
    # MoviePy expects RGB format, but OpenCV reads as BGR
    bg_img_rgb = cv2.cvtColor(bg_img, cv2.COLOR_BGR2RGB)
    height, width, _ = bg_img_rgb.shape

    # Define the visualizer style aesthetics 
    bar_width = int(width / num_bars) - 4
    max_bar_height = int(height * 0.35) # Max height is 35% of screen height
    fps = 30 # Standard YouTube shorts/music video framerate

    # Calculate padding to center the bars
    total_bars_width = (bar_width + 4) * num_bars
    start_x_offset = int((width - total_bars_width) / 2)
    
    audio_clip = AudioFileClip(audio_path)
    
    # Calculate crop if Shorts mode
    time_offset = 0
    if video_type == "short":
        total_duration = audio_clip.duration
        if total_duration > 60:
            # Pick a sweet spot between 30% to 60% of the song
            time_offset = random.uniform(total_duration * 0.3, total_duration * 0.6)
            if time_offset + 59 > total_duration:
                time_offset = total_duration - 59
            
            print(f"✂️  Shorts Mode: Snipping exactly 59s of audio from {time_offset:.1f}s")
            audio_clip = audio_clip.subclip(time_offset, time_offset + 59)
            duration = 59
        else:
            duration = total_duration
    else:
        duration = audio_clip.duration
    
    print("Building dynamic video frames. This will take time depending on your CPU...")
    # This function is called by MoviePy to generate the frame for time "t"
    def make_frame(t):
        # Calculate which audio index we are in at time 't', accounting for Shorts offset
        frame_idx = int(((t + time_offset) * sr) / 512)
        
        # Start with the clean background
        frame = bg_img_rgb.copy()
        
        # Get amplitudes for current index. Handle boundary in case it drifts.
        if frame_idx < S_normalized.shape[1]:
            current_amplitudes = S_normalized[:, frame_idx]
        else:
            current_amplitudes = np.zeros(num_bars)
            
        # Draw the visualizer "Monstercat" style bars floating at the bottom
        y_bottom = height - 50 # 50 pixels margin from bottom
        
        for i, val in enumerate(current_amplitudes):
            # Dynamic height depending on the beat volume
            bar_h = int(val * max_bar_height)
            
            # Position calculations
            x1 = start_x_offset + (i * (bar_width + 4))
            y1 = y_bottom - bar_h
            x2 = x1 + bar_width
            y2 = y_bottom
            
            # Aesthetic Neon Coloring (Magenta to Cyan mix based on height)
            r = int(255 * val)
            g = int(120 * (1-val))
            b = int(255)
            color = (r, g, b)
            
            # Paint the rectangle directly onto the frame copy
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
            
        return frame

    # Create the Video stream and attach the audio
    video = VideoClip(make_frame, duration=duration)
    video = video.set_audio(audio_clip)
    
    print("Exporting final MP4...")
    # Output properties optimized for speed and acceptable YouTube quality
    try:
        video.write_videofile(
            output_path, 
            fps=fps, 
            codec="libx264", 
            audio_codec="aac",
            threads=2, # Github actions typically gives 2 cores
            preset="ultrafast", # Required so GitHub Actions doesn't timeout
            logger=None # Suppress massive MoviePy output logging
        )
        print(f"Success! Final video rendered at: {output_path}")
        return output_path
    except Exception as e:
        print(f"Failed to render video: {e}")
        return False

if __name__ == "__main__":
    create_music_video(video_type="short")  # Testing code
