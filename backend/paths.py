import os
from pathlib import Path

# Persistent application data.
#
# Windows:  %LOCALAPPDATA%\GameLibrary
# Other OS: ~/.gamelibrary   (kept as a sane fallback for local dev)
if os.name == "nt":
    DATA_FOLDER = (
        Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
        / "GameLibrary"
    )
else:
    DATA_FOLDER = Path.home() / ".gamelibrary"

DATA_FOLDER.mkdir(parents=True, exist_ok=True)

# Where a user-picked custom wallpaper image gets copied to, so it survives
# app restarts/updates without depending on the original file staying put.
WALLPAPER_FOLDER = DATA_FOLDER / "wallpaper"
WALLPAPER_FOLDER.mkdir(parents=True, exist_ok=True)
