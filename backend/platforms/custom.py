import hashlib
import json
from pathlib import Path

from backend.paths import DATA_FOLDER

CUSTOM_GAMES_FILE = DATA_FOLDER / "custom_games.json"


def _load_games():
    if not CUSTOM_GAMES_FILE.exists():
        return []

    try:
        with CUSTOM_GAMES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

    except (OSError, json.JSONDecodeError):
        pass

    return []


def _save_games(games):
    DATA_FOLDER.mkdir(parents=True, exist_ok=True)

    with CUSTOM_GAMES_FILE.open("w", encoding="utf-8") as f:
        json.dump(games, f, indent=4, ensure_ascii=False)


def _make_id(exe_path):
    """
    Create a stable ID based on the absolute EXE path.
    """
    normalized = str(Path(exe_path).resolve()).lower()

    return hashlib.sha1(
        normalized.encode("utf-8")
    ).hexdigest()[:16]


def _game_name(exe_path):
    """
    Use the EXE filename as the default game name.
    """
    return Path(exe_path).stem


def import_exe(exe_path, name=None):
    """
    Add an EXE to the custom game library.

    Returns the created game dictionary.
    """

    if not exe_path:
        raise ValueError("No executable path provided.")

    path = Path(exe_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"Executable not found: {path}")

    if not path.is_file():
        raise ValueError("The selected path is not a file.")

    if path.suffix.lower() != ".exe":
        raise ValueError("Only .exe files can be imported.")

    games = _load_games()

    game_id = _make_id(path)

    # Don't add the same EXE twice
    for game in games:
        if game.get("id") == game_id:
            return game

    game_name = name.strip() if name and name.strip() else _game_name(path)

    game = {
        "platform": "custom",
        "id": game_id,
        "name": game_name,
        "launch_type": "exe",
        "exe_path": str(path),
        "launch_uri": None,
    }

    games.append(game)
    _save_games(games)

    return game


def remove_game(game_id):
    """
    Remove an imported custom game.
    """

    games = _load_games()

    new_games = [
        game
        for game in games
        if str(game.get("id")) != str(game_id)
    ]

    if len(new_games) == len(games):
        return False

    _save_games(new_games)

    return True


def scan():
    """
    Return all imported EXE games.
    """

    games = _load_games()

    valid_games = []

    for game in games:
        exe_path = game.get("exe_path")

        if not exe_path:
            continue

        # Keep the game in the library even if the EXE was moved/deleted.
        # This lets us show it and potentially let the user repair its path later.
        valid_games.append({
            "platform": "custom",
            "id": game.get("id"),
            "name": game.get("name", "Unknown Game"),
            "launch_type": "exe",
            "exe_path": exe_path,
            "launch_uri": None,
        })

    return valid_games