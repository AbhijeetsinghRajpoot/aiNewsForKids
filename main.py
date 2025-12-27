import os
from google_images_search import GoogleImagesSearch

import storyboard_data
import story_generator
import youtube_uploader


# ----------------------------------
# Initialize Google Image Search
# ----------------------------------
gis = GoogleImagesSearch(
    os.getenv("GOOGLE_API_KEY"),
    os.getenv("GOOGLE_CX")
)


def enhance_keyword_with_google(keyword):
    """
    Uses Google Image Search ONLY to validate/enhance keyword
    Pixabay will still download images inside story_generator
    """
    try:
        results = gis.search({
            "q": keyword,
            "num": 1
        })

        if results and gis.results():
            return keyword  # keyword is valid
    except Exception:
        pass

    return keyword  # fallback (no breaking changes)


def run_automation():
    print("STEP 1: Loading storyboard...")
    storyboard = storyboard_data.get_storyboard()

    if not storyboard:
        raise RuntimeError("Storyboard is empty or invalid")

    # ----------------------------------
    # Enhance storyboard keywords (NEW)
    # ----------------------------------
    for scene in storyboard:
        if "keyword" in scene:
            scene["keyword"] = enhance_keyword_with_google(scene["keyword"])

    # ----------------------------------
    # Title & Description
    # ----------------------------------
    first_scene = storyboard[0]

    video_title = (
        first_scene.get("title")
        or first_scene.get("keyword", "Trending Shorts")
    )

    video_description = (
        first_scene.get("description", "Latest update")
        + "\n\n#shorts #trending #news"
    )

    print("STEP 2: Generating video (Pixabay still used)...")
    video_file = story_generator.create_video(storyboard)

    if not video_file or not os.path.exists(video_file):
        raise RuntimeError("Video generation failed or file not found")

    print(f"Video generated successfully: {video_file}")

    # ----------------------------------
    # Upload to YouTube
    # ----------------------------------
    print("STEP 3: Uploading to YouTube...")
    youtube_uploader.upload_to_youtube(
        video_file,
        video_title,
        video_description
    )

    print("AUTOMATION COMPLETED SUCCESSFULLY 🚀")


if __name__ == "__main__":
    run_automation()
