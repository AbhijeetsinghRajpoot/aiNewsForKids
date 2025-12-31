import os
import sys

import storyboard_data
import story_generator
import youtube_uploader

# -----------------------------
# CONSTANTS
# -----------------------------
MAX_TITLE_LENGTH = 95  # YouTube Shorts safe
DEFAULT_HASHTAGS = "#shorts #collegefootball #football #sports #trending"

ASSETS_DIR = "assets"
VOICE_FILE = os.path.join(ASSETS_DIR, "voice.wav")


# -----------------------------
# SAFETY: ENSURE REQUIRED DIRS
# -----------------------------
def ensure_assets():
    """
    Ensure assets directory exists (CI-safe)
    """
    os.makedirs(ASSETS_DIR, exist_ok=True)
    print(f"Assets directory ready: {ASSETS_DIR}")


# -----------------------------
# TITLE (SHORTS OPTIMIZED)
# -----------------------------
def build_title(scene):
    title = (
        scene.get("title")
        or scene.get("keyword")
        or "🔥 College Football Bowl Game Highlights"
    ).strip()

    # Emoji hook for Shorts
    if not title.startswith(("🔥", "🏈", "🚨")):
        title = f"🔥 {title}"

    if len(title) > MAX_TITLE_LENGTH:
        title = title[: MAX_TITLE_LENGTH - 3] + "..."

    return title


# -----------------------------
# DESCRIPTION
# -----------------------------
def build_description(scene):
    description = scene.get(
        "description",
        "High-energy college football bowl game highlights."
    )

    description += (
        "\n\n"
        "🎬 Visuals: Pixabay (Royalty Free)\n"
        "📸 Images: Wikimedia Commons (CC)\n"
        "🎙️ Voice: AI Generated\n\n"
        f"{DEFAULT_HASHTAGS}"
    )

    return description


# -----------------------------
# MAIN AUTOMATION
# -----------------------------
def run_automation():
    print("STEP 0: Preparing environment...")
    ensure_assets()

    print("STEP 1: Loading storyboard...")
    storyboard = storyboard_data.get_storyboard()

    if not storyboard or not isinstance(storyboard, list):
        raise RuntimeError("Storyboard is empty or invalid")

    # -----------------------------
    # TITLE & DESCRIPTION
    # -----------------------------
    first_scene = storyboard[0]
    video_title = build_title(first_scene)
    video_description = build_description(first_scene)

    print(f"VIDEO TITLE: {video_title}")
    print("SHORTS MODE: ENABLED")

    # -----------------------------
    # GENERATE VIDEO
    # -----------------------------
    print("STEP 2: Generating video...")
    video_file = story_generator.create_video(
        storyboard=storyboard,
        voice_path=VOICE_FILE,   # ✅ EXPLICIT PATH
        shorts_mode=True
    )

    if not video_file or not os.path.exists(video_file):
        raise RuntimeError("Video generation failed — file not found")

    if not os.path.exists(VOICE_FILE):
        raise RuntimeError("TTS failed — voice.wav not created")

    print(f"Video generated successfully: {video_file}")

    # -----------------------------
    # UPLOAD TO YOUTUBE
    # -----------------------------
    print("STEP 3: Uploading to YouTube...")
    youtube_uploader.upload_to_youtube(
        video_file=video_file,
        title=video_title,
        description=video_description,
    )

    print("✅ AUTOMATION COMPLETED SUCCESSFULLY 🚀")


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    try:
        run_automation()
    except Exception as e:
        print("❌ AUTOMATION FAILED")
        print(str(e))
        sys.exit(1)
