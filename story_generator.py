import os
import requests
from PIL import Image
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips
)
from TTS.api import TTS

# ---------- ENVIRONMENT VARIABLES ----------
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

if not PIXABAY_API_KEY:
    raise RuntimeError("PIXABAY_API_KEY is not set")

# ---------- INITIALIZE COQUI TTS (CPU ONLY) ----------
tts_client = TTS(
    model_name="tts_models/en/ljspeech/fast_pitch",
    gpu=False
)

# ---------- CONSTANTS ----------
SHORT_WIDTH = 720
SHORT_HEIGHT = 1280
MAX_SHORT_DURATION = 59

# ---------- IMAGE SOURCE (PIXABAY) ----------
def download_pixabay_image(keyword, folder):
    url = "https://pixabay.com/api/"
    params = {
        "key": PIXABAY_API_KEY,
        "q": keyword,
        "image_type": "photo",
        "orientation": "vertical",
        "safesearch": "true",
        "per_page": 3
    }

    try:
        r = requests.get(url, params=params, timeout=10).json()
        if "hits" not in r or not r["hits"]:
            return None

        img_url = r["hits"][0]["largeImageURL"]
        img_path = os.path.join(folder, "raw.jpg")

        img_data = requests.get(img_url, timeout=10).content
        with open(img_path, "wb") as f:
            f.write(img_data)

        return img_path

    except Exception as e:
        print("Image download failed:", e)
        return None

# ---------- IMAGE NORMALIZATION (CRASH FIX) ----------
def normalize_image(input_path, output_path, size=(720, 1280)):
    with Image.open(input_path) as img:
        img = img.convert("RGB")
        img = img.resize(size, Image.Resampling.LANCZOS)
        img.save(output_path, "JPEG", quality=95)

# ---------- AUTO ZOOM EFFECT ----------
def ken_burns_effect(clip, zoom_factor=1.12):
    return clip.resize(
        lambda t: 1 + (zoom_factor - 1) * (t / clip.duration)
    )

# ---------- MAIN VIDEO FUNCTION ----------
def create_video(storyboard):
    video_segments = []
    total_duration = 0

    for i, entry in enumerate(storyboard):
        temp_img_folder = f"./temp_{i}"
        os.makedirs(temp_img_folder, exist_ok=True)

        # ---------- IMAGE ----------
        raw_img = download_pixabay_image(entry["keyword"], temp_img_folder)
        if not raw_img:
            print("Skipping scene, no image:", entry["keyword"])
            continue

        safe_img = os.path.join(temp_img_folder, "safe.jpg")
        normalize_image(raw_img, safe_img, size=(SHORT_WIDTH, SHORT_HEIGHT))

        # ---------- AUDIO ----------
        audio_path = f"audio_{i}.wav"
        tts_client.tts_to_file(
            text=entry["text"],
            file_path=audio_path
        )

        audio_clip = AudioFileClip(audio_path)

        if total_duration + audio_clip.duration > MAX_SHORT_DURATION:
            audio_clip = audio_clip.subclip(
                0, MAX_SHORT_DURATION - total_duration
            )

        total_duration += audio_clip.duration

        # ---------- VIDEO ----------
        img_clip = ImageClip(safe_img).set_duration(audio_clip.duration)
        img_clip = ken_burns_effect(img_clip)
        img_clip = img_clip.set_audio(audio_clip)

        video_segments.append(img_clip)

        if total_duration >= MAX_SHORT_DURATION:
            break

    if not video_segments:
        raise RuntimeError("No video segments created")

    final_video = concatenate_videoclips(video_segments, method="compose")

    final_video.write_videofile(
        "final_video.mp4",
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    return "final_video.mp4"