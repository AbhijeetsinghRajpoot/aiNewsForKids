import os
import sys

import script_generator
import story_generator
import youtube_uploader

MAX_TITLE_LENGTH = 95


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
def build_title(metadata):
    title = metadata.get("video_title", "Trending Update")

    if len(title) > MAX_TITLE_LENGTH:
        title = title[: MAX_TITLE_LENGTH - 3] + "..."

    return f"🔥 {title}"


# --------------------------------------------------
# DESCRIPTION
# --------------------------------------------------
def build_description(metadata):
    hashtags = " ".join(
        f"#{tag.replace(' ', '')}"
        for tag in metadata.get("tags", [])
    )

    return (
        f"{metadata.get('video_title')}\n\n"
        "📸 Images: Wikipedia (Wikimedia Commons)\n"
        "🎬 Videos: Pixabay (Royalty Free)\n"
        "🗣️ Voice: AI Generated\n\n"
        f"{hashtags} #shorts #trending"
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def run_automation(topic: str):
    prepare_environment()

    print("STEP 1: Generating storyboard...")
    data = script_generator.generate_full_storyboard(topic)

    metadata = data["metadata"]
    storyboard = data["scenes"]

    video_title = build_title(metadata)
    video_description = build_description(metadata)

    print(f"VIDEO TITLE: {video_title}")
    print("SHORTS MODE: ENABLED")

    print("STEP 2: Generating video...")
    video_file = story_generator.create_video(storyboard)

    if not video_file or not os.path.exists(video_file):
        raise RuntimeError("Video generation failed")

    print(f"Video generated: {video_file}")

    print("STEP 3: Uploading to YouTube...")
    youtube_uploader.upload_to_youtube(
        video_file=video_file,
        title=video_title,
        description=video_description
    )

    print("AUTOMATION COMPLETED SUCCESSFULLY 🚀")


if __name__ == "__main__":
    try:
        topic = sys.argv[1] if len(sys.argv) > 1 else "Breaking News"
        run_automation(topic)
    except Exception as e:
        print("❌ AUTOMATION FAILED")
        print(e)
        sys.exit(1)
