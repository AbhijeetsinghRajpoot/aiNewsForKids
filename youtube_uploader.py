from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
import os

def upload_to_youtube(video_file, title, description):
    """
    Upload a video to YouTube with proper error handling.

    Args:
        video_file (str): Path to the video file.
        title (str): Video title.
        description (str): Video description.

    Returns:
        dict or None: YouTube API response or None if failed.
    """
    # Check if token.json exists
    if not os.path.exists("token.json"):
        raise FileNotFoundError("token.json not found. Make sure your OAuth credentials are saved.")

    # Load credentials
    creds = Credentials.from_authorized_user_file('token.json')

    # Build YouTube service
    youtube = build('youtube', 'v3', credentials=creds)

    # Video metadata
    body = {
        "snippet": {
            "title": title + " #Shorts",
            "description": description + "\n\n#Shorts",
            "categoryId": "22",  # 'People & Blogs'
            "tags": ["AI Video", "Shorts", "Basketball", "Highlights"]
        },
        "status": {
            "privacyStatus": "public"  # public/private/unlisted
        }
    }

    try:
        print(f"Uploading video: {video_file}")
        media_body = MediaFileUpload(video_file, chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media_body
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Upload progress: {int(status.progress() * 100)}%")

        print("Upload completed!")
        print("Video ID:", response.get("id"))
        return response

    except HttpError as e:
        print("An HTTP error occurred:", e)
        return None
    except Exception as e:
        print("An unexpected error occurred:", e)
        return None
