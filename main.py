import os
import sys

import storyboard_data
import story_generator
import youtube_uploader


MAX_TITLE_LENGTH = 95  # Safe for YouTube Shorts
DEFAULT_HASHTAGS = "#shorts #cricket #womenscricket #trending #sports"


def build_title(scene):
    """
    Build a clean, Shorts-optimized title
    """
    title = (
        scene.get("title")
        or scene.get("keyword")
        or "Cricket Highlights"
    ).strip()

    if len(title) > MAX_TITLE_LENGTH:
        title = title[:MAX_TITLE_LENGTH - 3] + "..."

    return title


def build_description(scene):
    """
    Build a YouTube-safe description with attribution
    """
    description = scene.get("description", "Latest cricket update")

    description += (
        "\n\n"
        "📸 Images Source: Wikimedia Commons (Creative Commons)\n"
        "🎬 Background Videos: Pixabay (Royalty Free)\n\n"
        f"{DEFAULT_HASHTAGS}"
    )

    return description


def run_automation():
    print("STEP 1: Loading storyboard...")
    storyboard = storyboard_data.get_storyboard()

    if not storyboard or not isinstance(storyboard, list):
        raise RuntimeError("Storyboard is empty or invalid")

    # -----------------------------
    # Title & Description
    # -----------------------------
    first_scene = storyboard[0]
    video_title = build_title(first_scene)
    video_description = build_description(first_scene)

    print(f"VIDEO TITLE: {video_title}")

    # -----------------------------
    # Generate Video
    # -----------------------------
    print("STEP 2: Generating video...")
    video_file = story_generator.create_video(storyboard)

    if not video_file or not os.path.exists(video_file):
        raise RuntimeError("Video generation failed or file not found")

    print(f"Video generated successfully: {video_file}")

    # -----------------------------
    # Upload to YouTube ✅ FIXED
    # -----------------------------
    print("STEP 3: Uploading to YouTube...")
    youtube_uploader.upload_to_youtube(
        video_file=video_file,      # ✅ MUST match uploader signature
        title=video_title,
        description=video_description,
    )

    print("AUTOMATION COMPLETED SUCCESSFULLY 🚀")


if __name__ == "__main__":
    try:
        run_automation()
    except Exception as e:
        print("❌ AUTOMATION FAILED")
        print(e)
        sys.exit(1)
