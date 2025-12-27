import os
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips
)
from TTS.api import TTS

# ---------- ENVIRONMENT VARIABLES ----------
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

if not PIXABAY_API_KEY:
    raise RuntimeError("PIXABAY_API_KEY is not set")

# ---------- XTTS SPEAKER VOICE (AUTO-DOWNLOAD) ----------
SPEAKER_WAV = "assets/voice.wav"

def ensure_speaker_wav():
    os.makedirs("assets", exist_ok=True)

    if not os.path.exists(SPEAKER_WAV):
        print("XTTS speaker voice not found. Downloading default voice...")
        url = "https://github.com/coqui-ai/TTS/raw/dev/tests/data/ljspeech/wavs/LJ001-0001.wav"
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        with open(SPEAKER_WAV, "wb") as f:
            f.write(r.content)

ensure_speaker_wav()

# ---------- INITIALIZE COQUI XTTS ----------
tts_client = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    gpu=False
)

# ---------- CONSTANTS ----------
SHORT_WIDTH = 720
SHORT_HEIGHT = 1280
MAX_SHORT_DURATION = 59

# ---------- KEYWORD FALLBACKS ----------
KEYWORD_FALLBACKS = [
    "breaking news background",
    "sports stadium crowd",
    "cricket crowd cheering",
    "news studio background"
]

# ---------- PIXABAY VIDEO ----------
def download_pixabay_video(keyword, folder):
    url = "https://pixabay.com/api/videos/"
    params = {
        "key": PIXABAY_API_KEY,
        "q": keyword,
        "per_page": 3,
        "safesearch": "true"
    }

    try:
        r = requests.get(url, params=params, timeout=10).json()
        if not r.get("hits"):
            return None

        video_url = r["hits"][0]["videos"]["large"]["url"]
        path = os.path.join(folder, "raw.mp4")

        with open(path, "wb") as f:
            f.write(requests.get(video_url, timeout=15).content)

        return path
    except Exception as e:
        print("Video download failed:", e)
        return None

# ---------- PIXABAY IMAGE ----------
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
        if not r.get("hits"):
            return None

        img_url = r["hits"][0]["largeImageURL"]
        path = os.path.join(folder, "raw.jpg")

        with open(path, "wb") as f:
            f.write(requests.get(img_url, timeout=10).content)

        return path
    except Exception as e:
        print("Image download failed:", e)
        return None

# ---------- TEXT GRAPHIC FALLBACK ----------
def create_text_graphic(text, folder):
    img = Image.new("RGB", (SHORT_WIDTH, SHORT_HEIGHT), (10, 10, 10))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    wrapped = "\n".join(text[i:i + 28] for i in range(0, len(text), 28))
    draw.text((40, 400), wrapped, fill="white", font=font, spacing=10)

    path = os.path.join(folder, "fallback.jpg")
    img.save(path, "JPEG", quality=95)
    return path

# ---------- IMAGE NORMALIZATION ----------
def normalize_image(input_path, output_path):
    with Image.open(input_path) as img:
        img = img.convert("RGB")
        img = img.resize((SHORT_WIDTH, SHORT_HEIGHT), Image.Resampling.LANCZOS)
        img.save(output_path, "JPEG", quality=95)

# ---------- VIDEO NORMALIZATION ----------
def normalize_video(path, duration):
    clip = VideoFileClip(path)
    clip = clip.subclip(0, min(duration, clip.duration))
    clip = clip.resize(height=SHORT_HEIGHT)
    clip = clip.crop(x_center=clip.w / 2, width=SHORT_WIDTH)
    return clip

# ---------- KEN BURNS EFFECT ----------
def ken_burns_effect(clip, zoom_factor=1.1):
    return clip.resize(lambda t: 1 + (zoom_factor - 1) * (t / clip.duration))

# ---------- MAIN VIDEO CREATOR ----------
def create_video(storyboard):
    video_segments = []
    total_duration = 0

    for i, entry in enumerate(storyboard):
        folder = f"./temp_{i}"
        os.makedirs(folder, exist_ok=True)

        # ---------- AUDIO (XTTS – HINGLISH SAFE) ----------
        audio_path = f"audio_{i}.wav"
        tts_client.tts_to_file(
            text=entry["text"],
            file_path=audio_path,
            language="en",
            speaker_wav=SPEAKER_WAV
        )

        audio_clip = AudioFileClip(audio_path)

        if total_duration + audio_clip.duration > MAX_SHORT_DURATION:
            audio_clip = audio_clip.subclip(
                0, MAX_SHORT_DURATION - total_duration
            )

        duration = audio_clip.duration
        total_duration += duration

        # ---------- VISUAL ----------
        clip = None

        for kw in [entry["keyword"]] + KEYWORD_FALLBACKS:
            video_path = download_pixabay_video(kw, folder)
            if video_path:
                clip = normalize_video(video_path, duration)
                break

            image_path = download_pixabay_image(kw, folder)
            if image_path:
                safe = os.path.join(folder, "safe.jpg")
                normalize_image(image_path, safe)
                clip = ImageClip(safe).set_duration(duration)
                clip = ken_burns_effect(clip)
                break

        if not clip:
            fallback = create_text_graphic(entry["text"], folder)
            clip = ImageClip(fallback).set_duration(duration)

        clip = clip.set_audio(audio_clip)
        video_segments.append(clip)

        if total_duration >= MAX_SHORT_DURATION:
            break

    if not video_segments:
        raise RuntimeError("No video segments created")

    final = concatenate_videoclips(video_segments, method="compose")
    final.write_videofile(
        "final_video.mp4",
        fps=30,
        codec="libx264",
        audio_codec="aac"
    )

    return "final_video.mp4"