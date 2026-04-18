import os
import random
import requests
import urllib.parse
import cv2
from cv2 import dnn_superres

def generate_base_image(prompt, video_type="long", output_path="downloads/base_image.jpg"):
    """
    Generate an AI image using Pollinations.ai (Free API, no auth required).
    We generate at 1/2 resolution so our custom AI upscaler has room to enhance it.
    """
    print(f"Generating AI Image for prompt: '{prompt}' (Type: {video_type})...")
    encoded_prompt = urllib.parse.quote(prompt)
    
    if video_type == "short":
        width, height = 540, 960  # Upscales to 1080x1920 (Vertical 9:16)
    else:
        width, height = 960, 540  # Upscales to 1920x1080 (Wide 16:9)
        
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=True"

    
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"Base image generated and saved: {output_path}")
        return output_path
    else:
        print("Failed to download image from AI generator.")
        return None

def download_upscale_model(model_path="ESPCN_x2.pb"):
    """
    Downloads the ESPCN x2 super resolution AI model if not present locally.
    It's a fast, lightweight AI upscaler model that runs without a dedicated GPU.
    """
    # Publicly hosted ESPCN x2 model from TF-ESPCN project
    url = "https://github.com/fannymonori/TF-ESPCN/raw/master/export/ESPCN_x2.pb"
    if not os.path.exists(model_path):
        print(f"Downloading AI Super Resolution Model to '{model_path}'...")
        response = requests.get(url)
        with open(model_path, 'wb') as f:
            f.write(response.content)
        print("Model downloaded successfully.")
    return model_path

def upscale_image(image_path, model_path="ESPCN_x2.pb", output_path="downloads/background_hd.jpg"):
    """
    Uses OpenCV DNN SuperResolution to upsample the generated AI image.
    Note: REQUIRES `opencv-contrib-python` module (pip install opencv-contrib-python)
    """
    print(f"Upscaling image using custom AI upscaler model ({model_path})...")
    try:
        sr = dnn_superres.DnnSuperResImpl_create()
    except AttributeError:
        print("ERROR: OpenCV 'dnn_superres' module not found.")
        print("Please run: pip install opencv-contrib-python")
        return image_path # Fallback to base image
        
    img = cv2.imread(image_path)
    if img is None:
        print("Could not load image for upscaling.")
        return None

    # Load the model and configure scale
    sr.readModel(model_path)
    sr.setModel("espcn", 2)

    print("Upsampling in progress... This may take a few seconds.")
    # Provide the upscale calculation
    result = sr.upsample(img)

    cv2.imwrite(output_path, result)
    print(f"Image successfully upscaled and saved to: {output_path}")
    return output_path

def create_background(video_type="long"):
    os.makedirs("downloads", exist_ok=True)
    
    # Variety of aesthetic themes for randomized music videos
    themes = [
        "Aesthetic anime lofi room, neon lighting, dark night, rain outside",
        "Cyberpunk futuristic city street, neon glowing music vibes, 8k resolution, ultra detailed",
        "Beautiful cosmic galaxy landscape, glowing magical forest, music vibe, dark aesthetic",
        "Abstract sound wave geometry, minimalist dark background, glowing vibrant colors",
        "Retrowave sunset glitch art, synthwave background, grid grid glowing neon lines"
    ]
    
    # Pick a random style for the video
    prompt = random.choice(themes)
    
    base_file = generate_base_image(prompt, video_type)
    if base_file:
         model_file = download_upscale_model()
         upscaled_file = upscale_image(base_file, model_file)
         return upscaled_file
    return None

if __name__ == "__main__":
    result = create_background()
    if result:
        print("Success! Visual background is ready.")
