import json
import os

# The launcher writes one .item manifest file per installed game here.
MANIFESTS_DIR = os.environ.get(
    "EPIC_MANIFESTS_DIR",
    r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests",
)


def scan():
    """Return games in the platforms.scan() shape: [{platform, id, name, launch_uri}]."""
    if not os.path.isdir(MANIFESTS_DIR):
        return []

    games = []
    for file in os.listdir(MANIFESTS_DIR):
        if not file.lower().endswith(".item"):
            continue

        try:
            with open(os.path.join(MANIFESTS_DIR, file), "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        name = data.get("DisplayName")
        app_name = data.get("AppName")

        if not name or not app_name:
            continue

        namespace = data.get("CatalogNamespace")
        catalog_id = data.get("CatalogItemId")

        # The launcher accepts a bare AppName, but the fully-qualified
        # form is what Epic's own shortcuts use and is more reliable.
        if namespace and catalog_id:
            launch_key = f"{namespace}%3A{catalog_id}%3A{app_name}"
        else:
            launch_key = app_name

        games.append({
            "platform": "epic",
            "id": app_name,
            "name": name,
            "launch_uri": f"com.epicgames.launcher://apps/{launch_key}?action=launch&silent=true",
        })

    return games
