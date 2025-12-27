import os
import requests
import uuid

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")


def download_google_image(keyword, folder):
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return None

    os.makedirs(folder, exist_ok=True)

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": keyword,
        "searchType": "image",
        "num": 1,
        "imgSize": "LARGE",
        "safe": "active"
    }

    r = requests.get(url, params=params, timeout=10).json()
    if "items" not in r:
        return None

    image_url = r["items"][0]["link"]
    image_data = requests.get(image_url, timeout=10).content

    path = os.path.join(folder, f"{uuid.uuid4().hex}.jpg")
    with open(path, "wb") as f:
        f.write(image_data)

    return path
