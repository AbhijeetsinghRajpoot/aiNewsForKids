import os
import sys
import re

import storyboard_data
import story_generator
import youtube_uploader

MAX_TITLE_LENGTH = 95
MAX_HASHTAGS = 12


# --------------------------------------------------
# ENV SETUP
# --------------------------------------------------
def prepare_environment():
    print("STEP 0: Preparing environment...")
    os.makedirs("assets", exist_ok=True)
    print("Assets directory ready: assets")


# --------------------------------------------------
# TITLE
# --------------------------------------------------
def build_title(scene):
    title = scene.get("title") or scene.get("keyword") or "College Football Highlights"
    title = title.strip()

    if len(title) > MAX_TITLE_LENGTH:
        title = title[: MAX_TITLE_LENGTH - 3] + "..."

    return f"🔥 {title}"


# --------------------------------------------------
# HASHTAG GENERATOR
# --------------------------------------------------
def generate_hashtags(scene):
    hashtags = set()

    # From title
    title = scene.get("title", "")
    hashtags.update(title.lower().split())

    # From keyword
    keyword = scene.get("keyword", "")
    hashtags.update(keyword.lower().split())

    # From optional tags array
    extra_tags = scene.get("tags", [])
    for tag in extra_tags:
        hashtags.add(tag.lower().replace(" ", ""))

    # Cleanup words
    cleaned = []
    for tag in hashtags:
        tag = re.sub(r"[^a-z0-9]", "", tag)
        if len(tag) > 2:
            cleaned.append(f"#{tag}")

    # Add mandatory reach tags
    cleaned.extend(["#shorts", "#trending", "#sports"])

    # Deduplicate + limit
    final_tags = list(dict.fromkeys(cleaned))[:MAX_HASHTAGS]

    return " ".join(final_tags)


# --------------------------------------------------
# DESCRIPTION
# --------------------------------------------------
def build_description(scene):
    description = scene.get(
        "description",
        "Latest college football game updates, scores, and highlights."
    )

    hashtags = generate_hashtags(scene)

    description += (
        "\n\n📸 Images: Wikipedia (Wikimedia Commons)"
        "\n🎬 Videos: Pixabay (Royalty Free)"
        "\n🗣️ Voice: AI Generated\n\n"
        f"{hashtags}"
    )

    return description


# --------------------------------------------------
# MAIN AUTOMATION
# --------------------------------------------------
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
    print(f"HASHTAGS: {generate_hashtags(first_scene)}")
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
