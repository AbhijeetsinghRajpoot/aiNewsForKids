import requests

STORYBOARD_URL = (
    "https://raw.githubusercontent.com/"
    "prithvirajput510-web/storyboard-storage/main/scripts/storyboard_latest.json"
)

def get_storyboard():
    print("Fetching storyboard from storage repo...")

    response = requests.get(STORYBOARD_URL, timeout=15)
    response.raise_for_status()

    storyboard = response.json()

    if not isinstance(storyboard, list):
        raise ValueError("Invalid storyboard format (expected list)")

    return storyboard
