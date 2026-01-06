import os
import sys
import re

import storyboard_data
import story_generator
import youtube_uploader

MAX_TITLE_LENGTH = 95
MAX_HASHTAGS = 12


# --------------------------------------------------
# ENV
# --------------------------------------------------
def prepare_environment():
    print("STEP 0: Preparing environment...")
    os.makedirs("assets", exist_ok=True)
    print("Assets directory ready: assets")


# --------------------------------------------------
# TITLE (UNCHANGED LOGIC)
# --------------------------------------------------
def build_title(scene):
    title = scene.get("title") or scene.get("keyword") or "College Football Highlights"
    title = title.strip()

    if len(title) > MAX_TITLE_LENGTH:
        title = title[: MAX_TITLE_LENGTH - 3] + "..."

    return f"🔥 {title}"


# --------------------------------------------------
# DYNAMIC HASHTAGS (NEW)
# --------------------------------------------------
def generate_hashtags(storyboard):
    words = set()

    for scene in storyboard[:5]:  # first scenes = most relevant
        words.update(scene.get("keyword", "").lower().split())
        words.update(scene.get("identity_keyword", "").lower().split())
        words.update(scene.get("text", "").lower().split())

    hashtags = []
    for word in words:
        word = re.sub(r"[^a-z0-9]", "", word)
        if 3 <= len(word) <= 20:
            hashtags.append(f"#{word}")

    # mandatory reach tags
    hashtags.extend(["#shorts", "#trending"])

    # dedupe + limit
    return " ".join(list(dict.fromkeys(hashtags))[:MAX_HASHTAGS])


# --------------------------------------------------
# DESCRIPTION (DYNAMIC)
# --------------------------------------------------
def build_description(scene, storyboard):
    description = scene.get(
        "description",
        "Latest verified updates and highlights."
    )

    hashtags = generate_hashtags(storyboard)

    description += (
        "\n\n📸 Images: Wikipedia (Wikimedia Commons)"
        "\n🎬 Videos: Pixabay (Royalty Free)"
        "\n🗣️ Voice: AI Generated\n\n"
        f"{hashtags}"
    )

    return description


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def run_automation():
    prepare_environment()

    print("STEP 1: Loading storyboard...")
    storyboard = storyboard_data.get_storyboard()

    if not storyboard or not isinstance(storyboard, list):
        raise RuntimeError("Storyboard is empty or invalid")

    first_scene = storyboard[0]

    video_title = build_title(first_scene)
    video_description = build_description(first_scene, storyboard)

    print(f"VIDEO TITLE: {video_title}")
    print("SHORTS MODE: ENABLED")

    print("STEP 2: Generating video...")
    video_file = story_generator.create_video(storyboard)

    if not os.path.exists(video_file):
        raise RuntimeError("Video generation failed")

    print(f"Video generated successfully: {video_file}")

    print("STEP 3: Uploading to YouTube...")
    youtube_uploader.upload_to_youtube(
        video_file=video_file,
        title=video_title,
        description=video_description,
    )

    print("AUTOMATION COMPLETED SUCCESSFULLY 🚀")


# --------------------------------------------------
# ENTRY
# --------------------------------------------------
if __name__ == "__main__":
    try:
        run_automation()
    except Exception as e:
        print("❌ AUTOMATION FAILED")
        print(e)
        sys.exit(1)
