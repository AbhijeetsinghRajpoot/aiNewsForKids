import os
import math
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
        with open(SPEAKER_WAV, "wb") as f:
            f.write(requests.get(url, timeout=20).content)

ensure_speaker()

tts = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    gpu=False
)

# ============================================================
# VISUAL HELPERS
# ============================================================
def fit_image(src, dst):
    with Image.open(src).convert("RGB") as img:
        sw, sh = img.size
        scale = max(SHORT_W / sw, SHORT_H / sh)
        img = img.resize((int(sw * scale), int(sh * scale)), Image.Resampling.LANCZOS)
        left = (img.width - SHORT_W) // 2
        top = (img.height - SHORT_H) // 2
        img.crop((left, top, left + SHORT_W, top + SHORT_H)).save(dst, "JPEG", quality=95)

def ken_burns(clip, zoom=1.07):
    return clip.resize(lambda t: 1 + (zoom - 1) * (t / clip.duration))

# ============================================================
# MEDIA FETCH
# ============================================================
def pixabay_video(q, folder):
    r = requests.get("https://pixabay.com/api/videos/", params={
        "key": PIXABAY_API_KEY,
        "q": q,
        "per_page": 3,
        "safesearch": "true"
    }).json()

    if not r.get("hits"):
        return None

    url = r["hits"][0]["videos"]["large"]["url"]
    path = os.path.join(folder, "bg.mp4")
    with open(path, "wb") as f:
        f.write(requests.get(url).content)
    return path

def pixabay_image(q, folder):
    r = requests.get("https://pixabay.com/api/", params={
        "key": PIXABAY_API_KEY,
        "q": q,
        "orientation": "vertical",
        "per_page": 3
    }).json()

    if not r.get("hits"):
        return None

    path = os.path.join(folder, "bg.jpg")
    with open(path, "wb") as f:
        f.write(requests.get(r["hits"][0]["largeImageURL"]).content)
    return path

def wiki_image(q, folder):
    if not q:
        return None
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(q)}"
    r = requests.get(url, headers=HEADERS).json()
    img = r.get("thumbnail", {}).get("source")
    if not img or img.endswith(".svg"):
        return None
    path = os.path.join(folder, "wiki.jpg")
    with open(path, "wb") as f:
        f.write(requests.get(img).content)
    return path

# ============================================================
# ADVANCED WORD-SYNC SUBTITLES
# ============================================================
def subtitle_word_clips(text, duration):
    words = text.split()
    words_per_chunk = 3
    chunks = [
        " ".join(words[i:i + words_per_chunk])
        for i in range(0, len(words), words_per_chunk)
    ]

    per_chunk_time = duration / len(chunks)
    clips = []

    font_size = 64
    font = ImageFont.truetype("assets/Roboto-Bold.ttf", font_size)

    for i, chunk in enumerate(chunks):
        img = Image.new("RGBA", (SHORT_W, 220), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        w, h = get_text_size(d, chunk, font)
        y = 80

        d.rectangle(
            [(0, y - 25), (SHORT_W, y + h + 25)],
            fill=(0, 0, 0, 190)
        )

        d.text(
            ((SHORT_W - w) // 2, y),
            chunk,
            font=font,
            fill="#FFFFFF"
        )

        p = f"/tmp/sub_{i}.png"
        img.save(p)

        clips.append(
            ImageClip(p)
            .set_start(i * per_chunk_time)
            .set_duration(per_chunk_time)
            .set_position(("center", "bottom"))
        )

    return clips

# ============================================================
# MAIN
# ============================================================
def create_video(storyboard):
    final_clips = []
    total = 0

    for i, s in enumerate(storyboard):
        folder = f"temp_{i}"
        os.makedirs(folder, exist_ok=True)

        text = clean_text(s["text"])
        audio_path = f"{folder}/audio.wav"

        tts.tts_to_file(
            text=text,
            file_path=audio_path,
            speaker_wav=SPEAKER_WAV,
            language="en"
        )

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
            img = wiki_image(s.get("identity_keyword"), folder) or pixabay_image(s.get("keyword"), folder)
            safe = f"{folder}/safe.jpg"
            fit_image(img, safe)
            bg = ken_burns(ImageClip(safe).set_duration(duration))

        subs = subtitle_word_clips(text, duration)

        clip = CompositeVideoClip(
            [bg] + subs,
            size=(SHORT_W, SHORT_H)
        ).set_audio(audio)

        final_clips.append(clip)

        if total >= MAX_DURATION:
            break

    final = concatenate_videoclips(final_clips, method="compose")
    final.write_videofile(
        "final_video.mp4",
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=2
    )

    return "final_video.mp4"
