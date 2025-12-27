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
from google_images_search import GoogleImagesSearch

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")

if not PIXABAY_API_KEY:
    raise RuntimeError("PIXABAY_API_KEY is not set")

# ============================================================
# GOOGLE IMAGE SEARCH (OPTIONAL / FALLBACK)
# ============================================================
gis = None
if GOOGLE_API_KEY and GOOGLE_CX:
    gis = GoogleImagesSearch(GOOGLE_API_KEY, GOOGLE_CX)

# ============================================================
# XTTS SPEAKER VOICE
# ============================================================
SPEAKER_WAV = "assets/voice.wav"

def ensure_speaker_wav():
    os.makedirs("assets", exist_ok=True)

    if not os.path.exists(SPEAKER_WAV):
        print("XTTS speaker voice not found. Downloading default voice...")
        url = (
            "https://github.com/coqui-ai/TTS/raw/dev/tests/data/"
            "ljspeech/wavs/LJ001-0001.wav"
        )
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        with open(SPEAKER_WAV, "wb") as f:
            f.write(r.content)

ensure_speaker_wav()

# ============================================================
# INITIALIZE COQUI XTTS (CPU SAFE)
# ============================================================
tts_client = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    gpu=False
)

# ============================================================
# CONSTANTS
# ============================================================
SHORT_WIDTH = 720
SHORT_HEIGHT = 1280
MAX_SHORT_DURATION = 59

# ============================================================
# KEYWORD FALLBACKS (GENERIC MOTION)
# ============================================================
KEYWORD_FALLBACKS = [
    "football stadium crowd",
    "sports crowd cheering",
    "news studio background",
    "breaking news background"
]

# ============================================================
# PIXABAY VIDEO
# ============================================================
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
        path = os.path.join(folder, "pixabay.mp4")

        with open(path, "wb") as f:
            f.write(requests.get(video_url, timeout=15).content)

        return path
    except Exception as e:
        print("Pixabay video failed:", e)
        return None

# ============================================================
# PIXABAY IMAGE
# ============================================================
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
        path = os.path.join(folder, "pixabay.jpg")

        with open(path, "wb") as f:
            f.write(requests.get(img_url, timeout=10).content)

        return path
    except Exception as e:
        print("Pixabay image failed:", e)
        return None

# ============================================================
# GOOGLE IMAGE (IDENTITY ONLY)
# ============================================================
def download_google_image(keyword, folder):
    if not gis:
        return None

    try:
        gis.search({
            "q": keyword,
            "num": 1,
            "imgType": "photo",
            "imgSize": "large",
            "safe": "active"
        })

        results = gis.results()
        if not results:
            return None

        img = results[0]
        img.download(folder)

        downloaded = os.path.join(folder, img.filename)
        path = os.path.join(folder, "google.jpg")
        os.rename(downloaded, path)

        return path
    except Exception as e:
        print("Google image failed:", e)
        return None

# ============================================================
# TEXT GRAPHIC FALLBACK
# ============================================================
def create_text_graphic(text, folder):
    img = Image.new("RGB", (SHORT_WIDTH, SHORT_HEIGHT), (12, 12, 12))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    wrapped = "\n".join(text[i:i + 28] for i in range(0, len(text), 28))
    draw.text((40, 400), wrapped, fill="white", font=font, spacing=10)

    path = os.path.join(folder, "fallback.jpg")
    img.save(path, "JPEG", quality=95)
    return path

# ============================================================
# IMAGE NORMALIZATION
# ============================================================
def normalize_image(input_path, output_path):
    with Image.open(input_path) as img:
        img = img.convert("RGB")
        img = img.resize((SHORT_WIDTH, SHORT_HEIGHT), Image.Resampling.LANCZOS)
        img.save(output_path, "JPEG", quality=95)

# ============================================================
# VIDEO NORMALIZATION
# ============================================================
def normalize_video(path, duration):
    clip = VideoFileClip(path)
    clip = clip.subclip(0, min(duration, clip.duration))
    clip = clip.resize(height=SHORT_HEIGHT)
    clip = clip.crop(x_center=clip.w / 2, width=SHORT_WIDTH)
    return clip

# ============================================================
# KEN BURNS EFFECT
# ============================================================
def ken_burns_effect(clip, zoom_factor=1.18):
    return clip.resize(lambda t: 1 + (zoom_factor - 1) * (t / clip.duration))

# ============================================================
# MAIN VIDEO CREATOR
# ============================================================
def create_video(storyboard):
    video_segments = []
    total_duration = 0

    for i, entry in enumerate(storyboard):
        folder = f"./temp_{i}"
        os.makedirs(folder, exist_ok=True)

        # ---------------- AUDIO ----------------
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

        clip = None

        primary_kw = entry.get("keyword")
        identity_kw = entry.get("identity_keyword")

        keywords = []
        if primary_kw:
            keywords.append(primary_kw)
        keywords += KEYWORD_FALLBACKS

        # ---------------- VISUAL SELECTION ----------------
        for kw in keywords:
            # 1️⃣ Pixabay video (motion)
            video_path = download_pixabay_video(kw, folder)
            if video_path:
                clip = normalize_video(video_path, duration)
                break

            # 2️⃣ Pixabay image (context)
            image_path = download_pixabay_image(kw, folder)
            if image_path:
                safe = os.path.join(folder, "safe.jpg")
                normalize_image(image_path, safe)
                img_duration = min(duration, 3.5)
                clip = ImageClip(safe).set_duration(img_duration)
                clip = ken_burns_effect(clip)
                break

        # 3️⃣ Google image (identity only)
        if not clip and identity_kw:
            google_image = download_google_image(identity_kw, folder)
            if google_image:
                safe = os.path.join(folder, "safe_google.jpg")
                normalize_image(google_image, safe)
                img_duration = min(duration, 3.5)
                clip = ImageClip(safe).set_duration(img_duration)
                clip = ken_burns_effect(clip, zoom_factor=1.22)

        # 4️⃣ Text fallback
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
