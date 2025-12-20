import os
import requests
import numpy as np
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from openai import OpenAI

# ---------- ENV KEYS ----------
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- CONSTANTS ----------
SHORT_WIDTH = 720
SHORT_HEIGHT = 1280
MAX_SHORT_DURATION = 59

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- IMAGE SOURCES ----------

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

    r = requests.get(url, params=params).json()
    if "hits" not in r or not r["hits"]:
        return None

    img_url = r["hits"][0]["largeImageURL"]
    img_path = os.path.join(folder, "pixabay.jpg")

    with open(img_path, "wb") as f:
        f.write(requests.get(img_url).content)

    return img_path


def generate_openai_image(keyword, folder):
    prompt = (
        f"Photorealistic football scene, {keyword}, "
        "generic players, no logos, no text, no real people, "
        "cinematic lighting, professional sports photography"
    )

    result = openai_client.images.generate(
        model="gpt-image-1-mini",
        prompt=prompt,
        size="1024x1792"
    )

    img_url = result.data[0].url
    img_path = os.path.join(folder, "ai.jpg")

    with open(img_path, "wb") as f:
        f.write(requests.get(img_url).content)

    return img_path


# ---------- AUTO ZOOM EFFECT ----------

def ken_burns_effect(clip, zoom_factor=1.12):
    """
    Smooth zoom-in over time to simulate video motion
    """
    return clip.resize(
        lambda t: 1 + (zoom_factor - 1) * (t / clip.duration)
    )


# ---------- MAIN VIDEO FUNCTION ----------

def create_video(storyboard, client):
    video_segments = []
    total_duration = 0

    for i, entry in enumerate(storyboard):
        temp_img_folder = f"./temp_{i}"
        os.makedirs(temp_img_folder, exist_ok=True)

        # ---------- IMAGE SELECTION ----------
        img_path = download_pixabay_image(entry["keyword"], temp_img_folder)

        if img_path is None:
            print("Pixabay failed, generating AI image...")
            img_path = generate_openai_image(entry["keyword"], temp_img_folder)

        if img_path is None:
            print(f"No image for '{entry['keyword']}', skipping...")
            continue

        # ---------- AUDIO ----------
        audio_path = f"audio_{i}.mp3"
        audio_gen = client.text_to_speech.convert(
            text=entry["text"],
            voice_id="JBFqnCBsd6RMkjVDRZzb"
        )

        with open(audio_path, "wb") as f:
            for chunk in audio_gen:
                f.write(chunk)

        audio_clip = AudioFileClip(audio_path)

        if total_duration + audio_clip.duration > MAX_SHORT_DURATION:
            remaining = MAX_SHORT_DURATION - total_duration
            audio_clip = audio_clip.subclip(0, remaining)
            total_duration += remaining
        else:
            total_duration += audio_clip.duration

        # ---------- VIDEO CLIP ----------
        img_clip = ImageClip(img_path).set_duration(audio_clip.duration)

        img_clip = img_clip.resize(height=SHORT_HEIGHT)
        img_clip = img_clip.crop(
            x_center=img_clip.w / 2,
            y_center=SHORT_HEIGHT / 2,
            width=SHORT_WIDTH,
            height=SHORT_HEIGHT
        )

        # Apply auto zoom
        img_clip = ken_burns_effect(img_clip)

        img_clip = img_clip.set_audio(audio_clip)
        video_segments.append(img_clip)

        if total_duration >= MAX_SHORT_DURATION:
            break

    if not video_segments:
        raise ValueError("No video segments created.")

    final_video = concatenate_videoclips(video_segments, method="compose")
    output_name = "final_video.mp4"

    final_video.write_videofile(
        output_name,
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    return output_name
