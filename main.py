import os
import sys
import traceback
from datetime import datetime

import storyboard_data
import story_generator
import youtube_uploader


# -----------------------------
# CONSTANTS (SHORTS OPTIMIZED)
# -----------------------------
MAX_TITLE_LENGTH = 95  # YouTube Shorts safe
MIN_SCENES_REQUIRED = 3

DEFAULT_HASHTAGS = (
    "#shorts #cricket #indiancricket #trending #sports "
    "#viral #cricketshorts"
)

SHORTS_MODE = os.getenv("SHORTS_MODE", "false").lower() == "true"


# -----------------------------
# TITLE BUILDER (HOOK-FIRST)
# -----------------------------
def build_title(scene):
    """
    Build a Shorts-optimized, hook-driven title
    """
    raw_title = (
        scene.get("title")
        or scene.get("keyword")
        or "Indian Cricket Rising Stars"
    ).strip()

    # Strong hook for Shorts
    if SHORTS_MODE:
        raw_title = f"🔥 {raw_title}"

    if len(raw_title) > MAX_TITLE_LENGTH:
        raw_title = raw_title[: MAX_TITLE_LENGTH - 3] + "..."

    return raw_title


# -----------------------------
# DESCRIPTION BUILDER (CTR SAFE)
# -----------------------------
def build_description(scene):
    """
    Build Shorts-friendly YouTube description
    """
    base_description = scene.get(
        "description",
        "Latest Indian cricket updates, highlights, and rising stars."
    )

    description = (
        f"{base_description}\n\n"
        "⚡ Fast-paced cricket Shorts\n"
        "🏏 Domestic & International updates\n"
        "📈 Daily trending sports content\n\n"
        "📸 Images: Wikimedia Commons (Creative Commons)\n"
        "🎬 Videos: Pixabay (Royalty-Free)\n\n"
        f"{DEFAULT_HASHTAGS}"
    )

    return description


# -----------------------------
# STORYBOARD VALIDATION
# -----------------------------
def validate_storyboard(storyboard):
    if not storyboard or not isinstance(storyboard, list):
        raise RuntimeError("Storyboard is empty or invalid")

    if len(storyboard) < MIN_SCENES_REQUIRED:
        raise RuntimeError(
            f"Storyboard too short ({len(storyboard)} scenes). "
            f"Minimum required: {MIN_SCENES_REQUIRED}"
        )

    for idx, scene in enumerate(storyboard):
        if "text" not in scene or not scene["text"].strip():
            raise RuntimeError(f"Scene {idx} missing text")
        if "keyword" not in scene:
            raise RuntimeError(f"Scene {idx} missing keyword")


# -----------------------------
# MAIN AUTOMATION
# -----------------------------
def run_automation():
    start_time = datetime.utcnow()
    print("STEP 1: Loading storyboard...")

    storyboard = storyboard_data.get_storyboard()
    validate_storyboard(storyboard)

    # -----------------------------
    # Title & Description
    # -----------------------------
    first_scene = storyboard[0]
    video_title = build_title(first_scene)
    video_description = build_description(first_scene)

    print(f"VIDEO TITLE: {video_title}")
    print(f"SHORTS MODE: {'ENABLED' if SHORTS_MODE else 'DISABLED'}")

    # -----------------------------
    # Generate Video
    # -----------------------------
    print("STEP 2: Generating video...")
    video_file = story_generator.create_video(
        storyboard=storyboard,
        shorts_mode=SHORTS_MODE  # 🔥 enables fast cuts & captions
    )

    if not video_file or not os.path.exists(video_file):
        raise RuntimeError("Video generation failed or file not found")

    print(f"✅ Video generated: {video_file}")

    # -----------------------------
    # Upload to YouTube
    # -----------------------------
    print("STEP 3: Uploading to YouTube...")
    youtube_uploader.upload_to_youtube(
        video_file=video_file,
        title=video_title,
        description=video_description,
    )

    elapsed = (datetime.utcnow() - start_time).total_seconds()
    print(f"🚀 AUTOMATION COMPLETED in {elapsed:.1f}s")


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    try:
        run_automation()
    except Exception as e:
        print("❌ AUTOMATION FAILED")
        traceback.print_exc()
        sys.exit(1)
