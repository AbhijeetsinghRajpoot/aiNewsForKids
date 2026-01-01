import os
import sys

import storyboard_data
import story_generator
import youtube_uploader

MAX_TITLE_LENGTH = 95
DEFAULT_HASHTAGS = "#shorts #collegefootball #sports #highlights #trending"


def prepare_environment():
    print("STEP 0: Preparing environment...")
    os.makedirs("assets", exist_ok=True)
    print("Assets directory ready: assets")


def build_title(scene):
    title = scene.get("title") or scene.get("keyword") or "College Football Highlights"
    title = title.strip()

    if len(title) > MAX_TITLE_LENGTH:
        title = title[: MAX_TITLE_LENGTH - 3] + "..."

    return f"🔥 {title}"


def build_description(scene):
    description = scene.get(
        "description",
        "Latest college football bowl game updates and highlights."
    )

    description += (
        "\n\n📸 Images: Pixabay (Royalty Free)"
        "\n🎬 Videos: Pixabay (Royalty Free)"
        "\n🗣️ Voice: AI Generated\n\n"
        f"{DEFAULT_HASHTAGS}"
    )
    return description


def run_automation():
    prepare_environment()

    print("STEP 1: Loading storyboard...")
    storyboard = storyboard_data.get_storyboard()

    if not storyboard or not isinstance(storyboard, list):
        raise RuntimeError("Storyboard is empty or invalid")

    first_scene = storyboard[0]
    video_title = build_title(first_scene)
    video_description = build_description(first_scene)

    print(f"VIDEO TITLE: {video_title}")
    print("SHORTS MODE: ENABLED")

    print("STEP 2: Generating video...")
    video_file = story_generator.create_video(
        storyboard,
        shorts_mode=True  # ✅ ONLY this argument
    )

    if not os.path.exists(video_file):
        raise RuntimeError("Video generation failed")

    print(f"Video generated successfully: {video_file}")

    print("STEP 3: Uploading to YouTube...")
    youtube_uploader.upload_to_youtube(
        video_file=video_file,
        title=video_title,
        description=video_description
    )

    print("AUTOMATION COMPLETED SUCCESSFULLY 🚀")


if __name__ == "__main__":
    try:
        run_automation()
    except Exception as e:
        print("❌ AUTOMATION FAILED")
        print(e)
        sys.exit(1)