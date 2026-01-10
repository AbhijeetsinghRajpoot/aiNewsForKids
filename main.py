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
# TITLE (FROM METADATA)
# --------------------------------------------------
def build_title(metadata: dict) -> str:
    title = metadata.get("video_title", "Breaking Update").strip()

    if len(title) > MAX_TITLE_LENGTH:
        title = title[: MAX_TITLE_LENGTH - 3] + "..."

    return title


# --------------------------------------------------
# DYNAMIC HASHTAGS (FROM METADATA + SCENES)
# --------------------------------------------------
def generate_hashtags(metadata: dict, scenes: list) -> str:
    tags = []

    # 1️⃣ AI-generated tags (highest priority)
    for tag in metadata.get("tags", []):
        clean = re.sub(r"[^a-z0-9]", "", tag.lower())
        if clean:
            tags.append(f"#{clean}")

    # 2️⃣ Backup from scenes (if metadata is weak)
    if len(tags) < 6:
        words = set()
        for scene in scenes[:4]:
            words.update(scene.get("keyword", "").lower().split())
            words.update(scene.get("identity_keyword", "").lower().split())

        for word in words:
            word = re.sub(r"[^a-z0-9]", "", word)
            if 3 <= len(word) <= 20:
                tags.append(f"#{word}")

    # 3️⃣ Mandatory reach tags
    tags.extend(["#shorts", "#trending"])

    # Deduplicate + limit
    return " ".join(list(dict.fromkeys(tags))[:MAX_HASHTAGS])


# --------------------------------------------------
# DESCRIPTION (HIGH CTR)
# --------------------------------------------------
def build_description(metadata: dict, scenes: list) -> str:
    lead_text = scenes[0].get(
        "text",
        "Latest verified update."
    )

    hashtags = generate_hashtags(metadata, scenes)

    return (
        f"{lead_text}\n\n"
        "📸 Images: Wikipedia (Wikimedia Commons)\n"
        "🎬 Videos: Pixabay (Royalty Free)\n"
        "🗣️ Voice: AI Generated\n\n"
        f"{hashtags}"
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def run_automation():
    prepare_environment()

    print("STEP 1: Loading storyboard...")
    storyboard = storyboard_data.get_storyboard()

    if not storyboard or not isinstance(storyboard, list) or len(storyboard) < 2:
        raise RuntimeError("Storyboard format invalid")

    # ✅ Extract metadata + scenes
    metadata = storyboard[0]
    scenes = storyboard[1:]

    video_title = build_title(metadata)
    video_description = build_description(metadata, scenes)

    print(f"VIDEO TITLE: {video_title}")
    print("SHORTS MODE: ENABLED")

    print("STEP 2: Generating video...")
    video_file = story_generator.create_video(scenes)

    if not video_file or not os.path.exists(video_file):
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
