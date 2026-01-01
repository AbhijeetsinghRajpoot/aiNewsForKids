import os
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips
)
from TTS.api import TTS

# ============================================================
# ENV
# ============================================================
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
SHORTS_MODE = os.getenv("SHORTS_MODE", "false").lower() == "true"

if not PIXABAY_API_KEY:
    raise RuntimeError("PIXABAY_API_KEY missing")

# ============================================================
# CONSTANTS
# ============================================================
SHORT_WIDTH = 720
SHORT_HEIGHT = 1280
MAX_SHORT_DURATION = 59
MIN_SCENE_DURATION = 1.6
MAX_SCENE_DURATION = 4.2

KEYWORD_FALLBACKS = [
    "cricket stadium crowd",
    "domestic cricket match india",
    "cricket celebration fans"
]

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SPEAKER_WAV = "assets/voice.wav"

# ============================================================
# TTS
# ============================================================
tts_client = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    gpu=False
)

# ============================================================
# IMAGE HELPERS
# ============================================================
def fit_image(img_path, out_path):
    with Image.open(img_path) as img:
        img = img.convert("RGB")
        sw, sh = img.size
        scale = max(SHORT_WIDTH / sw, SHORT_HEIGHT / sh)
        nw, nh = int(sw * scale), int(sh * scale)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - SHORT_WIDTH) // 2
        top = (nh - SHORT_HEIGHT) // 2
        img = img.crop((left, top, left + SHORT_WIDTH, top + SHORT_HEIGHT))
        img.save(out_path, "JPEG", quality=95)

# ============================================================
# PIXABAY VIDEO / IMAGE DOWNLOAD
# ============================================================
def download_pixabay_video(keyword, folder):
    try:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": PIXABAY_API_KEY, "q": keyword, "per_page": 3, "safesearch": "true"},
            timeout=10
        ).json()
        if not r.get("hits"):
            return None
        url = r["hits"][0]["videos"]["large"]["url"]
        path = os.path.join(folder, "video.mp4")
        with open(path, "wb") as f:
            f.write(requests.get(url, timeout=15).content)
        print(f"[PIXABAY VIDEO] {keyword}")
        return path
    except Exception as e:
        print("[PIXABAY VIDEO ERROR]", e)
        return None

def download_pixabay_image(keyword, folder):
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={"key": PIXABAY_API_KEY, "q": keyword, "image_type": "photo", "orientation": "vertical", "per_page": 3, "safesearch": "true"},
            timeout=10
        ).json()
        if not r.get("hits"):
            return None
        url = r["hits"][0]["largeImageURL"]
        path = os.path.join(folder, "image.jpg")
        with open(path, "wb") as f:
            f.write(requests.get(url, timeout=10).content)
        print(f"[PIXABAY IMAGE] {keyword}")
        return path
    except Exception as e:
        print("[PIXABAY IMAGE ERROR]", e)
        return None

# ============================================================
# CAPTION (PIL-based)
# ============================================================
def create_caption_image(text, folder):
    img = Image.new("RGB", (SHORT_WIDTH, SHORT_HEIGHT), (10, 10, 10))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, 60)
    # Wrap text
    lines = []
    words = text.split()
    line = ""
    for w in words:
        test_line = line + " " + w if line else w
        w_size = draw.textsize(test_line, font=font)
        if w_size[0] > SHORT_WIDTH - 80:
            lines.append(line)
            line = w
        else:
            line = test_line
    lines.append(line)
    y = SHORT_HEIGHT - 400
    for l in lines:
        draw.text((40, y), l.upper(), fill="white", font=font)
        y += 70
    path = os.path.join(folder, "caption.jpg")
    img.save(path, "JPEG", quality=95)
    return path

# ============================================================
# DYNAMIC ZOOM (SHORTS STYLE)
# ============================================================
def dynamic_zoom(clip):
    return clip.resize(lambda t: 1 + 0.12 * (t / clip.duration))

# ============================================================
# MAIN VIDEO CREATOR
# ============================================================
def create_video(storyboard, shorts_mode=False):
    segments = []
    total_time = 0

    for i, scene in enumerate(storyboard):
        folder = f"./temp_{i}"
        os.makedirs(folder, exist_ok=True)

        # -------- AUDIO --------
        audio_path = os.path.join(folder, "audio.wav")
        tts_client.tts_to_file(
            text=scene["text"],
            file_path=audio_path,
            speaker_wav=SPEAKER_WAV,
            language="en"
        )
        audio = AudioFileClip(audio_path)

        duration = min(max(audio.duration, MIN_SCENE_DURATION), MAX_SCENE_DURATION)
        if total_time + duration > MAX_SHORT_DURATION:
            break
        audio = audio.subclip(0, duration)
        total_time += duration

        clip = None

        # -------- VIDEO --------
        if scene.get("visual_type") == "emotion":
            clip_path = download_pixabay_video(scene["keyword"], folder)
            if clip_path:
                base = VideoFileClip(clip_path).subclip(0, duration)
                base = base.resize(height=SHORT_HEIGHT).crop(width=SHORT_WIDTH)
                clip = dynamic_zoom(base)

        # -------- IMAGE --------
        if not clip:
            img_path = download_pixabay_image(scene["keyword"], folder)
            if img_path:
                safe_path = os.path.join(folder, "safe.jpg")
                fit_image(img_path, safe_path)
                clip = dynamic_zoom(ImageClip(safe_path).set_duration(duration))

        # -------- TEXT FALLBACK --------
        if not clip:
            safe_path = os.path.join(folder, "fallback.jpg")
            img = Image.new("RGB", (SHORT_WIDTH, SHORT_HEIGHT), (15, 15, 15))
            img.save(safe_path)
            clip = ImageClip(safe_path).set_duration(duration)

        # -------- CAPTION --------
        caption_path = create_caption_image(scene["text"], folder)
        caption_clip = ImageClip(caption_path).set_duration(duration).set_position(("center", SHORT_HEIGHT - 400))
        clip = CompositeVideoClip([clip, caption_clip]).set_audio(audio)

        segments.append(clip)
        if total_time >= MAX_SHORT_DURATION:
            break

    final_clip = concatenate_videoclips(segments, method="compose")
    final_clip.write_videofile(
        "final_video.mp4",
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=2,
        preset="ultrafast"
    )

    return "final_video.mp4"