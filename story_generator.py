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

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

if not PIXABAY_API_KEY:
    raise RuntimeError("PIXABAY_API_KEY is not set")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (YouTubeShortsBot/1.0)",
    "Referer": "https://en.wikipedia.org/"
}

# ============================================================
# XTTS SPEAKER VOICE
# ============================================================
SPEAKER_WAV = "assets/voice.wav"

def ensure_speaker_wav():
    os.makedirs("assets", exist_ok=True)
    if not os.path.exists(SPEAKER_WAV):
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
# INITIALIZE TTS
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

KEYWORD_FALLBACKS = [
    "cricket stadium crowd",
    "domestic cricket match India",
    "cricket celebration"
]

# ============================================================
# IMAGE UTILITIES
# ============================================================
def fit_image_to_viewport(src, dst):
    with Image.open(src) as img:
        img = img.convert("RGB")
        sw, sh = img.size
        scale = max(SHORT_WIDTH / sw, SHORT_HEIGHT / sh)

        nw, nh = int(sw * scale), int(sh * scale)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)

        left = (nw - SHORT_WIDTH) // 2
        top = (nh - SHORT_HEIGHT) // 2
        img = img.crop((left, top, left + SHORT_WIDTH, top + SHORT_HEIGHT))
        img.save(dst, "JPEG", quality=95)

# ============================================================
# PIXABAY VIDEO
# ============================================================
def download_pixabay_video(keyword, folder):
    try:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={
                "key": PIXABAY_API_KEY,
                "q": keyword,
                "per_page": 3,
                "safesearch": "true",
            },
            timeout=10
        ).json()

        if not r.get("hits"):
            return None

        url = r["hits"][0]["videos"]["large"]["url"]
        path = os.path.join(folder, "pixabay.mp4")

        with open(path, "wb") as f:
            f.write(requests.get(url, timeout=15).content)

        print(f"[PIXABAY VIDEO] {keyword}")
        return path

    except Exception as e:
        print("[PIXABAY VIDEO ERROR]", e)
        return None

# ============================================================
# PIXABAY IMAGE
# ============================================================
def download_pixabay_image(keyword, folder):
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": PIXABAY_API_KEY,
                "q": keyword,
                "image_type": "photo",
                "orientation": "vertical",
                "safesearch": "true",
                "per_page": 3,
            },
            timeout=10
        ).json()

        if not r.get("hits"):
            return None

        url = r["hits"][0]["largeImageURL"]
        path = os.path.join(folder, "pixabay.jpg")

        with open(path, "wb") as f:
            f.write(requests.get(url, timeout=10).content)

        print(f"[PIXABAY IMAGE] {keyword}")
        return path

    except Exception as e:
        print("[PIXABAY IMAGE ERROR]", e)
        return None

# ============================================================
# ✅ WIKIMEDIA REST IMAGE (SAFE & FINAL)
# ============================================================
def download_wikipedia_image(keyword, folder):
    try:
        title = keyword.replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()

        thumbnail = data.get("thumbnail", {}).get("source")
        if not thumbnail:
            return None

        if thumbnail.lower().endswith(".svg"):
            return None

        path = os.path.join(folder, "wikipedia.jpg")

        img = requests.get(thumbnail, headers=HEADERS, timeout=10)
        img.raise_for_status()

        with open(path, "wb") as f:
            f.write(img.content)

        # Validate image
        with Image.open(path) as im:
            im.verify()

        print(f"[WIKIPEDIA IMAGE] {keyword}")
        return path

    except Exception as e:
        print("[WIKIPEDIA ERROR]", e)
        return None

# ============================================================
# VIDEO HELPERS
# ============================================================
def normalize_video(path, duration):
    clip = VideoFileClip(path)
    clip = clip.subclip(0, min(duration, clip.duration))
    clip = clip.resize(height=SHORT_HEIGHT)
    return clip.crop(x_center=clip.w / 2, width=SHORT_WIDTH)

def ken_burns(clip, zoom=1.12):
    return clip.resize(lambda t: 1 + (zoom - 1) * (t / clip.duration))

# ============================================================
# TEXT FALLBACK
# ============================================================
def create_text_graphic(text, folder):
    img = Image.new("RGB", (SHORT_WIDTH, SHORT_HEIGHT), (10, 10, 10))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    wrapped = "\n".join(text[i:i + 30] for i in range(0, len(text), 30))
    draw.text((40, 420), wrapped, fill="white", font=font, spacing=12)
    path = os.path.join(folder, "fallback.jpg")
    img.save(path, "JPEG", quality=95)
    return path

# ============================================================
# MAIN VIDEO CREATOR
# ============================================================
def create_video(storyboard):
    segments = []
    total = 0

    for i, entry in enumerate(storyboard):
        folder = f"./temp_{i}"
        os.makedirs(folder, exist_ok=True)

        # ---------- AUDIO ----------
        audio_path = f"{folder}/audio.wav"
        tts_client.tts_to_file(
            text=entry["text"],
            file_path=audio_path,
            language="en",
            speaker_wav=SPEAKER_WAV,
        )

        audio = AudioFileClip(audio_path)
        remaining = MAX_SHORT_DURATION - total
        if remaining <= 0:
            break

        audio = audio.subclip(0, min(audio.duration, remaining))
        duration = audio.duration
        total += duration

        visual_type = entry.get("visual_type", "emotion")
        keyword = entry.get("keyword")
        identity_kw = entry.get("identity_keyword")

        clip = None

        # ---------- PIXABAY VIDEO ----------
        if visual_type == "emotion":
            for kw in [keyword] + KEYWORD_FALLBACKS:
                if not kw:
                    continue
                video = download_pixabay_video(kw, folder)
                if video:
                    clip = normalize_video(video, duration)
                    break

        # ---------- WIKIPEDIA IMAGE ----------
        if not clip and visual_type == "identity" and identity_kw:
            img = download_wikipedia_image(identity_kw, folder)
            if img:
                try:
                    safe = os.path.join(folder, "safe.jpg")
                    fit_image_to_viewport(img, safe)
                    clip = ken_burns(ImageClip(safe).set_duration(duration))
                except Exception:
                    clip = None

        # ---------- PIXABAY IMAGE ----------
        if not clip and keyword:
            img = download_pixabay_image(keyword, folder)
            if img:
                safe = os.path.join(folder, "safe.jpg")
                fit_image_to_viewport(img, safe)
                clip = ken_burns(ImageClip(safe).set_duration(duration))

        # ---------- TEXT FALLBACK ----------
        if not clip:
            fallback = create_text_graphic(entry["text"], folder)
            clip = ImageClip(fallback).set_duration(duration)

        segments.append(clip.set_audio(audio))

        if total >= MAX_SHORT_DURATION:
            break

    final = concatenate_videoclips(segments, method="compose")
    final.write_videofile(
        "final_video.mp4",
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=2,
    )

    return "final_video.mp4"
