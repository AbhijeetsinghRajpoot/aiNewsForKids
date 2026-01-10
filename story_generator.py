import os
import requests
import urllib.parse
import unicodedata
from PIL import Image, ImageDraw, ImageFont
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips
)
from TTS.api import TTS

# ============================================================
# ENVIRONMENT
# ============================================================
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
if not PIXABAY_API_KEY:
    raise RuntimeError("PIXABAY_API_KEY is not set")

HEADERS = {
    "User-Agent": "YouTubeShortsBot/1.0",
    "Referer": "https://en.wikipedia.org/"
}

SHORT_WIDTH = 720
SHORT_HEIGHT = 1280
MAX_SHORT_DURATION = 59

KEYWORD_FALLBACKS = [
    "breaking news background",
    "news studio background",
    "world map animation"
]

SPEAKER_WAV = "assets/voice.wav"

# ============================================================
# TEXT CLEANING (XTTS SAFE)
# ============================================================
def clean_text(text):
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode()

# ============================================================
# SPEAKER VOICE
# ============================================================
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
# TTS
# ============================================================
tts_client = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    gpu=False
)

# ============================================================
# IMAGE / VIDEO HELPERS
# ============================================================
def fit_image_to_viewport(src, dst):
    try:
        with Image.open(src) as img:
            img = img.convert("RGB")
            sw, sh = img.size
            scale = max(SHORT_WIDTH / sw, SHORT_HEIGHT / sh)
            nw, nh = int(sw * scale), int(sh * scale)
            img = img.resize((nw, nh), Image.Resampling.LANCZOS)
            left = (nw - SHORT_WIDTH) // 2
            top = (nh - SHORT_HEIGHT) // 2
            img.crop((left, top, left + SHORT_WIDTH, top + SHORT_HEIGHT)).save(
                dst, "JPEG", quality=95
            )
        return True
    except Exception as e:
        print("[IMAGE FIT FAILED]", e)
        return False

def ken_burns(clip, zoom=1.08):
    return clip.resize(lambda t: 1 + (zoom - 1) * (t / clip.duration))

def normalize_video(path, duration):
    src = VideoFileClip(path)
    clip = src.subclip(0, min(duration, src.duration))
    clip = clip.resize(height=SHORT_HEIGHT)
    clip = clip.crop(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=SHORT_WIDTH,
        height=SHORT_HEIGHT
    )
    return clip

# ============================================================
# PIXABAY
# ============================================================
def download_pixabay_video(keyword, folder):
    try:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={
                "key": PIXABAY_API_KEY,
                "q": keyword,
                "per_page": 3,
                "safesearch": "true"
            },
            timeout=10
        ).json()

        if not r.get("hits"):
            return None

        url = r["hits"][0]["videos"]["large"]["url"]
        path = os.path.join(folder, "pixabay.mp4")
        with open(path, "wb") as f:
            f.write(requests.get(url, timeout=15).content)

        return path
    except:
        return None

def download_pixabay_image(keyword, folder):
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": PIXABAY_API_KEY,
                "q": keyword,
                "orientation": "vertical",
                "per_page": 3
            },
            timeout=10
        ).json()

        if not r.get("hits"):
            return None

        url = r["hits"][0]["largeImageURL"]
        path = os.path.join(folder, "pixabay.jpg")

        with open(path, "wb") as f:
            f.write(requests.get(url, timeout=10).content)

        with Image.open(path) as im:
            im.verify()

        return path
    except:
        return None

# ============================================================
# WIKIPEDIA IMAGE
# ============================================================
def download_wikipedia_image(keyword, folder):
    try:
        if not keyword:
            return None

        title = urllib.parse.quote(keyword.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()

        thumb = data.get("thumbnail", {}).get("source")
        if not thumb or thumb.lower().endswith(".svg"):
            return None

        path = os.path.join(folder, "wiki.jpg")
        img_resp = requests.get(thumb, headers=HEADERS, timeout=10)
        img_resp.raise_for_status()

        with open(path, "wb") as f:
            f.write(img_resp.content)

        with Image.open(path) as im:
            im.verify()

        return path
    except:
        return None

# ============================================================
# NEWS SUBTITLE GENERATOR
# ============================================================
def create_news_subtitle(text, folder):
    img = Image.new("RGBA", (SHORT_WIDTH, 220), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("assets/Roboto-Bold.ttf", 46)
    except:
        font = ImageFont.load_default()

    max_chars = 28
    words = text.split()
    lines, line = [], ""
    for w in words:
        if len(line + " " + w) <= max_chars:
            line += (" " if line else "") + w
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)

    text_height = len(lines) * 55
    bg_y = 220 - text_height - 20

    draw.rectangle(
        [(0, bg_y), (SHORT_WIDTH, 220)],
        fill=(0, 0, 0, 180)
    )

    y = bg_y + 10
    for l in lines:
        w, h = draw.textsize(l, font=font)
        draw.text(
            ((SHORT_WIDTH - w) // 2, y),
            l,
            font=font,
            fill="white"
        )
        y += 55

    path = os.path.join(folder, "subtitle.png")
    img.save(path)
    return path

# ============================================================
# MAIN VIDEO GENERATOR
# ============================================================
def create_video(storyboard):
    segments = []
    total = 0

    for i, entry in enumerate(storyboard):
        folder = f"./temp_{i}"
        os.makedirs(folder, exist_ok=True)

        print(f"[SCENE {i}] START")

        audio_path = f"{folder}/audio.wav"
        tts_text = clean_text(entry["text"])

        tts_client.tts_to_file(
            text=tts_text,
            file_path=audio_path,
            language="en",
            speaker_wav=SPEAKER_WAV
        )

        audio = AudioFileClip(audio_path)
        remaining = MAX_SHORT_DURATION - total
        if remaining <= 0:
            break

        audio = audio.subclip(0, min(audio.duration, remaining))
        duration = audio.duration
        total += duration

        clip = None

        if entry.get("visual_type") == "emotion":
            for kw in [entry.get("keyword")] + KEYWORD_FALLBACKS:
                video = download_pixabay_video(kw, folder)
                if video:
                    clip = ken_burns(normalize_video(video, duration))
                    break

        if not clip and entry.get("visual_type") == "identity":
            img = download_wikipedia_image(entry.get("identity_keyword"), folder)
            if img:
                safe = f"{folder}/safe.jpg"
                if fit_image_to_viewport(img, safe):
                    clip = ken_burns(ImageClip(safe).set_duration(duration))

        if not clip:
            img = download_pixabay_image(entry.get("keyword"), folder)
            if img:
                safe = f"{folder}/safe.jpg"
                if fit_image_to_viewport(img, safe):
                    clip = ken_burns(ImageClip(safe).set_duration(duration))

        subtitle_img = create_news_subtitle(tts_text, folder)
        subtitle_clip = (
            ImageClip(subtitle_img)
            .set_duration(duration)
            .set_position(("center", "bottom"))
        )

        final_clip = CompositeVideoClip(
            [clip, subtitle_clip],
            size=(SHORT_WIDTH, SHORT_HEIGHT)
        ).set_audio(audio)

        segments.append(final_clip)

        print(f"[SCENE {i}] DONE ({duration:.2f}s)")

        if total >= MAX_SHORT_DURATION:
            break

    final = concatenate_videoclips(segments, method="compose")
    final.write_videofile(
        "final_video.mp4",
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=2
    )

    return "final_video.mp4"
