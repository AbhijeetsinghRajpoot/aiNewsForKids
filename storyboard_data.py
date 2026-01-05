import requests

STORYBOARD_URL = (
    "https://raw.githubusercontent.com/"
    "prithvirajput510-web/storyboard-storage/main/storyboard_latest.json"
)

def get_storyboard():
    print("Fetching storyboard from storage repo...")

    response = requests.get(STORYBOARD_URL, timeout=15)
    response.raise_for_status()

    storyboard = response.json()

    if not isinstance(storyboard, list):
        raise ValueError(
            f"Invalid storyboard format: expected list, got {type(storyboard)}"
        )

    if not storyboard:
        raise ValueError("Storyboard is empty")

    return storyboard
