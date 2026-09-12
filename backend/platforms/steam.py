import os
import re

STEAM_FOLDER = os.environ.get(
    "STEAM_FOLDER",
    r"C:\Program Files (x86)\Steam\steamapps",
)
BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
# Kept outside backend/ on purpose: uvicorn --reload watches that folder,
# and new images landing inside it would trigger endless restarts.
IMAGE_FOLDER = os.path.join(PROJECT_ROOT, "images")

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# 228980 is the Steamworks Common Redistributables package, not a real game.
SKIP_APP_IDS = {"228980"}


def _parse_acf(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    appid_match = re.search(r'"appid"\s+"(\d+)"', content)
    if not appid_match:
        return None

    name_match = re.search(r'"name"\s+"([^"]+)"', content)

    return {
        "appid": appid_match.group(1),
        "name": name_match.group(1) if name_match else f"App {appid_match.group(1)}",
    }


def scan():
    """Return games in the platforms.scan() shape: [{platform, id, name, launch_uri}]."""
    if not os.path.isdir(STEAM_FOLDER):
        return []

    games = []
    for file in os.listdir(STEAM_FOLDER):
        if not file.lower().endswith(".acf"):
            continue

        parsed = _parse_acf(os.path.join(STEAM_FOLDER, file))
        if not parsed or parsed["appid"] in SKIP_APP_IDS:
            continue

        games.append({
            "platform": "steam",
            "id": parsed["appid"],
            "name": parsed["name"],
            "launch_uri": f"steam://rungameid/{parsed['appid']}",
        })

    return games


