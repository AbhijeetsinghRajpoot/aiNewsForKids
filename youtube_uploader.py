from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

def upload_to_youtube(video_file, title, description):
    creds = Credentials.from_authorized_user_file('token.json')
    youtube = build('youtube', 'v3', credentials=creds)

    body = {
        "snippet": {
            "title": title + " #Shorts",
            "description": description + "\n\n#Shorts",
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public"
        }
    }

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(video_file, resumable=True)
    )

    return request.execute()