import json

from backend.paths import DATA_FOLDER

SETTINGS_FILE = DATA_FOLDER / "settings.json"

# Backend is the source of truth for settings (the frontend also keeps a
# localStorage copy for instant-apply on boot before pywebview's API bridge
# is ready), so everything the user changes -- accent color, wallpaper,
# controller inversion -- survives app restarts even if the webview's own
# storage is ever cleared.
DEFAULT_SETTINGS = {
    "accentColor": "#ff2b2b",
    # "none" | "custom" | "current_game"
    "wallpaperMode": "none",
    "wallpaperImage": None,
    "wallpaperOpacity": 35,
    "wallpaperDarken": 55,
    "glassEffect": True,
    "wallpaperBlur": 18,
    "invertY": False,
    "invertX": False,
}


def load_settings():
    if not SETTINGS_FILE.exists():
        return dict(DEFAULT_SETTINGS)

    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            return merged

    except (OSError, json.JSONDecodeError):
        pass

    return dict(DEFAULT_SETTINGS)


def save_settings(patch):
    """
    Merge `patch` into the settings already on disk and persist the result.
    Returns the full, merged settings dict.
    """
    DATA_FOLDER.mkdir(parents=True, exist_ok=True)

    current = load_settings()

    if isinstance(patch, dict):
        current.update(patch)

    with SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(current, f, indent=4, ensure_ascii=False)

    return current
