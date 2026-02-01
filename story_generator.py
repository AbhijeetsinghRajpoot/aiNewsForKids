import os
import requests
import urllib.parse
import unicodedata
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# PILLOW 10+ COMPATIBILITY
# ============================================================
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

def get_text_size(draw, text, font):
    if hasattr(draw, "textbbox"):
        b = draw.textbbox((0, 0), text, font=font)
        return b[2] - b[0], b[3] - b[1]
    return draw.textsize(text, font=font)

from moviepy.editor import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips
)

from TTS.api import TTS

# ============================================================
# CONFIG
# ============================================================
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
if not PIXABAY_API_KEY:
    raise RuntimeError("PIXABAY_API_KEY missing")

SHORT_W, SHORT_H = 720, 1280
MAX_DURATION = 59
SPEAKER_WAV = "assets/voice.wav"
FALLBACK_IMG = "assets/fallback.jpg"

HEADERS = {
    "User-Agent": "ShortsBot/1.0",
    "Referer": "https://en.wikipedia.org/"
}

KEYWORD_FALLBACKS = [
    "breaking news background",
    "world economy",
    "sports crowd stadium"
]

# ============================================================
# UTILS
# ============================================================
def clean_text(text):
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode()

def ensure_speaker():
    os.makedirs("assets", exist_ok=True)
    if not os.path.exists(SPEAKER_WAV):
        url = "https://github.com/coqui-ai/TTS/raw/dev/tests/data/ljspeech/wavs/LJ001-0001.wav"
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        with open(SPEAKER_WAV, "wb") as f:
            f.write(r.content)

def ensure_fallback():
    os.makedirs("assets", exist_ok=True)
    if not os.path.exists(FALLBACK_IMG):
        img = Image.new("RGB", (SHORT_W, SHORT_H), (30, 30, 30))
        img.save(FALLBACK_IMG)

ensure_speaker()
ensure_fallback()

tts = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    gpu=False
)

# ============================================================
# VISUAL HELPERS
# ============================================================
def fit_image(src, dst):
    if not src or not os.path.exists(src):
        return False
    try:
        with Image.open(src).convert("RGB") as img:
            sw, sh = img.size
            scale = max(SHORT_W / sw, SHORT_H / sh)
            img = img.resize((int(sw * scale), int(sh * scale)), Image.Resampling.LANCZOS)
            left = (img.width - SHORT_W) // 2
            top = (img.height - SHORT_H) // 2
            img.crop((left, top, left + SHORT_W, top + SHORT_H)).save(dst, "JPEG", quality=95)
        return True
    except:
        return False

def ken_burns(clip, zoom=1.07):
    return clip.resize(lambda t: 1 + (zoom - 1) * (t / clip.duration))

# ============================================================
# MEDIA FETCH
# ============================================================
def pixabay_video(q, folder):
    try:
        r = requests.get("https://pixabay.com/api/videos/", params={
            "key": PIXABAY_API_KEY,
            "q": q,
            "per_page": 3,
            "safesearch": "true"
        }, timeout=10).json()

        if not r.get("hits"):
            return None

        url = r["hits"][0]["videos"]["large"]["url"]
        path = os.path.join(folder, "bg.mp4")
        with open(path, "wb") as f:
            f.write(requests.get(url, timeout=15).content)
        return path
    except:
        return None

def pixabay_image(q, folder):
    try:
        r = requests.get("https://pixabay.com/api/", params={
            "key": PIXABAY_API_KEY,
            "q": q,
            "orientation": "vertical",
            "per_page": 3
        }, timeout=10).json()

        if not r.get("hits"):
            return None

        path = os.path.join(folder, "bg.jpg")
        with open(path, "wb") as f:
            f.write(requests.get(r["hits"][0]["largeImageURL"], timeout=10).content)

        Image.open(path).verify()
        return path
    except:
        return None

def wiki_image(q, folder):
    if not q:
        return None
    try:
        api = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(q)}"
        r = requests.get(api, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None

        data = r.json()
        img = data.get("thumbnail", {}).get("source")
        if not img or img.lower().endswith((".svg", ".webp")):
            return None

        path = os.path.join(folder, "wiki.jpg")
        with open(path, "wb") as f:
            f.write(requests.get(img, timeout=10).content)

        Image.open(path).verify()
        return path
    except:
        return None

# ============================================================
# SUBTITLES
# ============================================================
def subtitle_word_clips(text, duration):
    words = text.split()
    chunk_size = 3
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    per = duration / len(chunks)
    clips = []

    try:
        font = ImageFont.truetype("assets/Roboto-Bold.ttf", 64)
    except:
        font = ImageFont.load_default()

    for i, chunk in enumerate(chunks):
        img = Image.new("RGBA", (SHORT_W, 220), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        w, h = get_text_size(d, chunk, font)
        y = 80

        d.rectangle([(0, y - 25), (SHORT_W, y + h + 25)], fill=(0, 0, 0, 190))
        d.text(((SHORT_W - w) // 2, y), chunk, font=font, fill="white")

        p = f"temp_sub_{i}.png"
        img.save(p)

        clips.append(ImageClip(p).set_start(i * per).set_duration(per).set_position(("center", "bottom")))

    return clips

# ============================================================
# MAIN
# ============================================================
def create_video(storyboard):
    final = []
    total = 0

    for i, s in enumerate(storyboard):
        folder = f"temp_{i}"
        os.makedirs(folder, exist_ok=True)

        text = clean_text(s["text"])
        audio_path = f"{folder}/audio.wav"

        tts.tts_to_file(text=text, file_path=audio_path, speaker_wav=SPEAKER_WAV, language="en")

        audio = AudioFileClip(audio_path)
        duration = min(audio.duration, MAX_DURATION - total)
        total += duration

        bg = None

        if s.get("visual_type") == "emotion":
            for k in [s.get("keyword")] + KEYWORD_FALLBACKS:
                v = pixabay_video(k, folder)
                if v:
                    bg = ken_burns(VideoFileClip(v).subclip(0, duration).resize(height=SHORT_H))
                    break

        if not bg:
            img = (
                wiki_image(s.get("identity_keyword"), folder)
                or pixabay_image(s.get("keyword"), folder)
                or FALLBACK_IMG
            )

            safe = f"{folder}/safe.jpg"
            ok = fit_image(img, safe)
            if not ok:
                fit_image(FALLBACK_IMG, safe)

            bg = ken_burns(ImageClip(safe).set_duration(duration))

        subs = subtitle_word_clips(text, duration)

        clip = CompositeVideoClip([bg] + subs, size=(SHORT_W, SHORT_H)).set_audio(audio)
        final.append(clip)

        if total >= MAX_DURATION:
            break

    out = concatenate_videoclips(final, method="compose")
    out.write_videofile("final_video.mp4", fps=30, codec="libx264", audio_codec="aac", threads=2)

    return "final_video.mp4"
