import os
import time
import argparse
from downloader import download_random_ncs_song
from image_gen import create_background
from video_compiler import create_music_video
from uploader import run_upload

def run_ncs_automation(video_type="long"):
    print("==================================================")
    print(f"  🚀 STARTING NCS YOUTUBE BOT ({video_type.upper()} MODE)")
    print("==================================================")
    
    # STEP 1: Get Audio
    print("\n>>> STEP 1: Fetching Music...")
    audio_path, title = download_random_ncs_song("downloads")
    if not audio_path:
        print("Pipeline Failed at Step 1.")
        return
        
    # STEP 2: Get Background AI Image
    print("\n>>> STEP 2: Generating AI Visuals...")
    image_path = create_background(video_type)
    if not image_path:
        print("Pipeline Failed at Step 2.")
        return
        
    # STEP 3: Render Final Video with Visualizer Overlay
    print("\n>>> STEP 3: Compiling Music Video with Visualizer...")
    video_path = "downloads/final_video.mp4"
    
    success = create_music_video(audio_path, image_path, video_path, video_type)
    if not success:
        print("Pipeline Failed at Step 3.")
        return
        
    # STEP 4: Upload to YouTube
    print("\n>>> STEP 4: Uploading to YouTube...")
    upload_success = run_upload(video_path, title, video_type)
    
    if upload_success:
        print("\n🎉 AUTOMATION PIPELINE COMPLETED SUCCESSFULLY! 🎉")
        
        # Cleanup heavy generated files to save GitHub Storage Space
        print("🧹 Cleaning up workspace to prevent disk bloat...")
        try:
            if os.path.exists(audio_path): os.remove(audio_path)
            if os.path.exists(image_path): os.remove(image_path)
            if os.path.exists(video_path): os.remove(video_path)
            print("Cleanup finished successfully.")
        except Exception as e:
            print(f"Warning: Failed to cleanup some files natively: {e}")
            
    else:
        print("\n❌ Pipeline Failed at Final Upload Step.")
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NCS YouTube Music Bot")
    parser.add_argument("--type", choices=["long", "short"], default="long", help="Generate a full 16:9 video or a 9:16 Short")
    args = parser.parse_args()
    
    run_ncs_automation(args.type)
