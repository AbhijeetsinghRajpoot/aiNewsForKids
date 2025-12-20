import os
from elevenlabs.client import ElevenLabs
import storyboard_data
import story_generator
import youtube_uploader


# ---------- ENV VALIDATION ----------
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not ELEVENLABS_API_KEY:
    raise RuntimeError("❌ ELEVENLABS_API_KEY is not set in environment variables")


# ---------- INITIALIZE CLIENTS ----------
el_client = ElevenLabs(
    api_key=ELEVENLABS_API_KEY
)


def run_automation():
    print("Step 1: Loading Storyboard...")
    storyboard = storyboard_data.get_storyboard()

    if not storyboard:
        raise RuntimeError("❌ Storyboard is empty")

    # Title & description
    video_title = storyboard[0].get("title", storyboard[0]["keyword"]) + " #Shorts"
    video_description = storyboard[0].get("description", "") + "\n\n#Shorts"

    print("Step 2: Generating Video...")
    video_file = story_generator.create_video(
        storyboard=storyboard,
        client=el_client
    )

    if not video_file or not os.path.exists(video_file):
        raise RuntimeError("❌ Video generation failed")

    print("Step 3: Uploading to YouTube...")
    youtube_uploader.upload_to_youtube(
        video_file,
        video_title,
        video_description
    )

    print("✅ Automation completed successfully!")


if __name__ == "__main__":
    run_automation()
