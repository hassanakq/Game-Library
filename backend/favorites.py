import json

from backend.paths import DATA_FOLDER

FAVORITES_FILE = DATA_FOLDER / "favorites.json"


def _key(platform, game_id):
    return f"{platform}:{game_id}"


def _load():
    if not FAVORITES_FILE.exists():
        return []

    try:
        with FAVORITES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            # de-dupe while preserving order
            seen = set()
            cleaned = []
            for item in data:
                if isinstance(item, str) and item not in seen:
                    seen.add(item)
                    cleaned.append(item)
            return cleaned

    except (OSError, json.JSONDecodeError):
        pass

    return []


def _save(favorites):
    DATA_FOLDER.mkdir(parents=True, exist_ok=True)

    with FAVORITES_FILE.open("w", encoding="utf-8") as f:
        json.dump(favorites, f, indent=4, ensure_ascii=False)


def get_favorites():
    """
    Return the list of favorite keys, "<platform>:<id>".
    """
    return _load()


def is_favorite(platform, game_id):
    return _key(platform, game_id) in _load()


def set_favorite(platform, game_id, favorite):
    """
    Add or remove a game from favorites.

    Returns the resulting favorite state (bool).
    """
    favorites = _load()
    key = _key(platform, game_id)

    if favorite:
        if key not in favorites:
            favorites.append(key)
    else:
        favorites = [item for item in favorites if item != key]

    _save(favorites)

    return favorite


def toggle_favorite(platform, game_id):
    """
    Flip the favorite state of a game and return the new state (bool).
    """
    favorites = _load()
    key = _key(platform, game_id)

    if key in favorites:
        favorites = [item for item in favorites if item != key]
        _save(favorites)
        return False

    favorites.append(key)
    _save(favorites)
    return True
