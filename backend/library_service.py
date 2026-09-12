from backend.platforms import (
    epic,
    gog,
    steam,
    ubisoft,
    ea,
    battlenet,
    custom,
)
SCANNERS = {
    "steam": steam.scan,
    "epic": epic.scan,
    "gog": gog.scan,
    "ubisoft": ubisoft.scan,
    "ea": ea.scan,
    "battlenet": battlenet.scan,
    "custom": custom.scan,
}


def get_all_games():
    games = []

    for platform, scanner in SCANNERS.items():
        try:
            games.extend(scanner())
        except Exception:
            # A launcher that isn't installed, or has an install layout
            # we didn't anticipate, shouldn't take the whole library down.
            continue

    games.sort(key=lambda g: g["name"].lower())
    return games
