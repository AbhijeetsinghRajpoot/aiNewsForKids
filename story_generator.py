import os
import requests
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips
)
from TTS.api import TTS


# ---------- ENVIRONMENT VARIABLES ----------
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

if not PIXABAY_API_KEY:
    raise RuntimeError("❌ PIXABAY_API_KEY is not set")


# ---------- INITIALIZE COQUI TTS ----------
tts_client = TTS(
    model_name="tts_models/en/ljspeech/fast_pitch",
    gpu=False  # REQUIRED for GitHub Actions
)


# ---------- CONSTANTS ----------
SHORT_WIDTH = 720
SHORT_HEIGHT = 1280
MAX_SHORT_DURATION = 59


# ---------- IMAGE SOURCE (PIXABAY ONLY) ----------
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

    r = requests.get(url, params=params, timeout=10).json()
    if "hits" not in r or not r["hits"]:
        return None

    img_url = r["hits"][0]["largeImageURL"]
    img_path = os.path.join(folder, "pixabay.jpg")

    with open(img_path, "wb") as f:
        f.write(requests.get(img_url, timeout=10).content)

    return img_path


# ---------- AUTO ZOOM EFFECT ----------
def ken_burns_effect(clip, zoom_factor=1.12):
    return clip.resize(
        lambda t: 1 + (zoom_factor - 1) * (t / clip.duration)
    )


# ---------- MAIN VIDEO FUNCTION ----------
def create_video(storyboard, tts_client=tts_client):
    video_segments = []
    total_duration = 0

    for i, entry in enumerate(storyboard):
        temp_img_folder = f"./temp_{i}"
        os.makedirs(temp_img_folder, exist_ok=True)

        # ---------- IMAGE ----------
        img_path = download_pixabay_image(entry["keyword"], temp_img_folder)
        if img_path is None:
            print(f"⚠️ No image found for: {entry['keyword']}")
            continue

        # ---------- AUDIO (COQUI TTS) ----------
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
        img_clip = ImageClip(img_path).set_duration(audio_clip.duration)

        img_clip = img_clip.resize(height=SHORT_HEIGHT)
        img_clip = img_clip.crop(
            x_center=img_clip.w / 2,
            y_center=SHORT_HEIGHT * 0.45,
            width=SHORT_WIDTH,
            height=SHORT_HEIGHT
        )

        img_clip = ken_burns_effect(img_clip)
        img_clip = img_clip.set_audio(audio_clip)

        video_segments.append(img_clip)

        if total_duration >= MAX_SHORT_DURATION:
            break

    if not video_segments:
        raise ValueError("❌ No video segments created.")

    final_video = concatenate_videoclips(video_segments, method="compose")

    final_video.write_videofile(
        "final_video.mp4",
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    return "final_video.mp4"