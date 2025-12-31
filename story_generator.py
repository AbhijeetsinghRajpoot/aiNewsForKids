import os
import requests
from PIL import Image
from moviepy.editor import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    TextClip,
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
# CONSTANTS (SHORTS RETENTION TUNED)
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

ASSETS_DIR = "assets"
DEFAULT_SPEAKER_WAV = os.path.join(ASSETS_DIR, "voice.wav")

# ============================================================
# ENSURE SPEAKER WAV (CI SAFE)
# ============================================================
def ensure_speaker_wav(path):
    os.makedirs(ASSETS_DIR, exist_ok=True)

    if os.path.exists(path):
        return path

    print("Downloading default speaker voice...")
    url = (
        "https://github.com/coqui-ai/TTS/raw/dev/tests/data/"
        "ljspeech/wavs/LJ001-0001.wav"
    )
    r = requests.get(url, timeout=20)
    r.raise_for_status()

    with open(path, "wb") as f:
        f.write(r.content)

    return path


# ============================================================
# TTS INIT (ONCE)
# ============================================================
tts_client = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    gpu=False
)

# ============================================================
# IMAGE HELPERS
# ============================================================
def fit_image(img_path, out):
    with Image.open(img_path) as img:
        img = img.convert("RGB")
        sw, sh = img.size
        scale = max(SHORT_WIDTH / sw, SHORT_HEIGHT / sh)
        img = img.resize((int(sw * scale), int(sh * scale)))
        left = (img.width - SHORT_WIDTH) // 2
        top = (img.height - SHORT_HEIGHT) // 2
        img = img.crop((left, top, left + SHORT_WIDTH, top + SHORT_HEIGHT))
        img.save(out, "JPEG", quality=92)


# ============================================================
# VISUAL DOWNLOADERS
# ============================================================
def download_pixabay_video(keyword, folder):
    try:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": PIXABAY_API_KEY, "q": keyword, "per_page": 3},
            timeout=10
        ).json()

        if not r.get("hits"):
            return None

        url = r["hits"][0]["videos"]["large"]["url"]
        path = f"{folder}/video.mp4"

        with open(path, "wb") as f:
            f.write(requests.get(url, timeout=15).content)

        print(f"[PIXABAY VIDEO] {keyword}")
        return path
    except Exception:
        return None


def download_pixabay_image(keyword, folder):
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={"key": PIXABAY_API_KEY, "q": keyword, "per_page": 3},
            timeout=10
        ).json()

        if not r.get("hits"):
            return None

        url = r["hits"][0]["largeImageURL"]
        path = f"{folder}/image.jpg"

        with open(path, "wb") as f:
            f.write(requests.get(url, timeout=10).content)

        print(f"[PIXABAY IMAGE] {keyword}")
        return path
    except Exception:
        return None


# ============================================================
# CAPTIONS (RETENTION BOOST)
# ============================================================
def caption_clip(text, duration):
    return (
        TextClip(
            text.upper(),
            fontsize=56,
            font=FONT_PATH,
            color="white",
            method="caption",
            size=(640, None),
            align="center"
        )
        .set_duration(duration)
        .set_position(("center", 900))
    )


# ============================================================
# ZOOM EFFECT (SHORTS STYLE)
# ============================================================
def dynamic_zoom(clip):
    return clip.resize(lambda t: 1 + 0.10 * (t / clip.duration))


# ============================================================
# MAIN CREATOR
# ============================================================
def create_video(storyboard, voice_path=DEFAULT_SPEAKER_WAV, shorts_mode=False):
    segments = []
    total_time = 0

    speaker_wav = ensure_speaker_wav(voice_path)

    for i, scene in enumerate(storyboard):
        folder = f"./temp_{i}"
        os.makedirs(folder, exist_ok=True)

        # -------- AUDIO --------
        audio_path = f"{folder}/audio.wav"
        tts_client.tts_to_file(
            text=scene["text"],
            file_path=audio_path,
            speaker_wav=speaker_wav,
            language="en"
        )

        audio = AudioFileClip(audio_path)

        duration = min(
            max(audio.duration, MIN_SCENE_DURATION),
            MAX_SCENE_DURATION
        )

        if total_time + duration > MAX_SHORT_DURATION:
            break

        audio = audio.subclip(0, duration)
        total_time += duration

        clip = None

        # -------- VIDEO FIRST --------
        video = download_pixabay_video(scene.get("keyword"), folder)
        if video:
            base = VideoFileClip(video).subclip(0, duration)
            base = base.resize(height=SHORT_HEIGHT)
            base = base.crop(x_center=base.w / 2, width=SHORT_WIDTH)
            clip = dynamic_zoom(base)

        # -------- IMAGE --------
        if not clip:
            img = download_pixabay_image(scene.get("keyword"), folder)
            if img:
                safe = f"{folder}/safe.jpg"
                fit_image(img, safe)
                clip = dynamic_zoom(ImageClip(safe).set_duration(duration))

        # -------- TEXT FALLBACK --------
        if not clip:
            clip = ImageClip(
                Image.new("RGB", (SHORT_WIDTH, SHORT_HEIGHT), (15, 15, 15))
            ).set_duration(duration)

        # -------- CAPTIONS --------
        caption = caption_clip(scene["text"], duration)
        final_clip = CompositeVideoClip([clip, caption]).set_audio(audio)

        segments.append(final_clip)

        if total_time >= MAX_SHORT_DURATION:
            break

    final = concatenate_videoclips(segments, method="compose")
    final.write_videofile(
        "final_video.mp4",
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=2,
        preset="ultrafast"
    )

    return "final_video.mp4"
