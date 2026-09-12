import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.controller import controller
from backend.favorites import get_favorites, toggle_favorite
from backend.image_resolver import (
    IMAGE_FOLDER,
    has_local_image,
    local_image_url,
    resolve_image,
)
from backend.library_service import get_all_games
from backend.paths import WALLPAPER_FOLDER
from backend.platforms.custom import import_exe, remove_game
from backend.settings_store import load_settings, save_settings


class GameLibraryAPI:
    """
    Exposed to the frontend as `window.pywebview.api`.

    Anything that needs the native window (file dialogs, window
    chrome, the controller) lives here instead of behind a
    regular HTTP endpoint.
    """

    # ------------------------------------------------------------
    # Importing games
    # ------------------------------------------------------------

    def select_game(self):
        """
        Open the native Windows file picker.
        """

        import webview

        window = webview.windows[0]

        result = window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=(
                "Executable files (*.exe)",
                "All files (*.*)",
            ),
        )

        if not result:
            return {
                "success": False,
                "cancelled": True,
            }

        exe_path = result[0]

        try:
            game = import_exe(exe_path)

            # Automatically search for artwork
            resolve_image(
                game["platform"],
                game["id"],
                game["name"],
            )

            return {
                "success": True,
                "game": game,
                "image_url": local_image_url(
                    game["platform"],
                    game["id"],
                ),
            }

        except Exception as exc:
            return {
                "success": False,
                "message": str(exc),
            }

    def remove_custom_game(self, game_id):
        """
        Remove a game that was imported through "import .exe".

        The frontend is responsible for confirming with the user
        first; this call performs the removal itself.
        """
        try:
            removed = remove_game(game_id)

            return {
                "success": bool(removed),
                "message": None if removed else "Game not found",
            }

        except Exception as exc:
            return {
                "success": False,
                "message": str(exc),
            }

    # ------------------------------------------------------------
    # Settings (accent color, wallpaper, controller inversion, ...)
    #
    # The backend is the source of truth: settings live in a JSON file
    # under the app's data folder so they persist across restarts even if
    # the webview's own storage is ever reset.
    # ------------------------------------------------------------

    def get_settings(self):
        return load_settings()

    def save_settings(self, settings):
        try:
            return {
                "success": True,
                "settings": save_settings(settings or {}),
            }
        except Exception as exc:
            return {
                "success": False,
                "message": str(exc),
            }

    def select_wallpaper_image(self):
        """
        Open the native file picker for an image, copy it into the app's
        data folder (so it survives even if the original file gets moved
        or deleted), and return a URL the frontend can use directly.
        """
        import webview

        window = webview.windows[0]

        result = window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=(
                "Image files (*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif)",
                "All files (*.*)",
            ),
        )

        if not result:
            return {
                "success": False,
                "cancelled": True,
            }

        src = Path(result[0])

        if not src.is_file():
            return {
                "success": False,
                "message": "File not found",
            }

        ext = src.suffix.lower() or ".jpg"

        # Clear out any previously-saved custom wallpaper first so stale
        # files (from a different extension) don't pile up over time.
        for old in WALLPAPER_FOLDER.glob("custom.*"):
            try:
                old.unlink()
            except OSError:
                pass

        dest = WALLPAPER_FOLDER / f"custom{ext}"

        try:
            shutil.copyfile(src, dest)
        except Exception as exc:
            return {
                "success": False,
                "message": str(exc),
            }

        return {
            "success": True,
            # Cache-bust: without this the browser may keep showing the old
            # picture if the new one happens to share the same filename.
            "image_url": f"/wallpaper/{dest.name}?t={int(time.time())}",
        }

    # ------------------------------------------------------------
    # Native window chrome
    # ------------------------------------------------------------

    def _window(self):
        import webview

        return webview.windows[0]

    def minimize_window(self):
        self._window().minimize()
        return {"success": True}

    def toggle_maximize_window(self):
        window = self._window()

        # pywebview doesn't expose a boolean "is maximized" flag that's
        # consistent across every backend, so we track state ourselves
        # via a simple attribute stashed on the window object.
        is_maximized = getattr(window, "_gamelibrary_maximized", False)

        if is_maximized:
            window.restore()
            window._gamelibrary_maximized = False
        else:
            window.maximize()
            window._gamelibrary_maximized = True

        return {
            "success": True,
            "maximized": window._gamelibrary_maximized,
        }

    def close_window(self):
        self._window().destroy()
        return {"success": True}

    def toggle_fullscreen(self):
        self._window().toggle_fullscreen()
        return {"success": True}

    def get_window_size(self):
        """
        Current window geometry, used by the frontend's edge/corner drag
        handles to compute the new size while the mouse moves.
        """
        window = self._window()

        return {
            "x": window.x,
            "y": window.y,
            "width": window.width,
            "height": window.height,
        }

    # Maps a resize-handle direction (as used by the CSS/JS drag handles)
    # to the corner/edge of the window that should stay put while the
    # opposite edge(s) move. E.g. dragging the "e" (east/right) edge should
    # keep the left edge fixed, so we fix WEST.
    _FIX_POINTS = {
        "n": "SOUTH",
        "s": "NORTH",
        "e": "WEST",
        "w": "EAST",
        "ne": "SOUTH_WEST",
        "nw": "SOUTH_EAST",
        "se": "NORTH_WEST",
        "sw": "NORTH_EAST",
    }

    def resize_window(self, width, height, direction="se"):
        """
        Resize the frameless window from a given edge/corner.

        pywebview windows are frameless here, so the OS can't draw a resize
        border for us; the frontend tracks the mouse itself (see the
        `.resize-handle` elements + app.js) and calls this repeatedly while
        dragging. `fix_point` tells pywebview which corner should stay
        anchored so resizing from the top/left edges doesn't make the
        window jump.
        """
        from webview.window import FixPoint

        window = self._window()

        min_w, min_h = window.min_size
        width = max(int(width), int(min_w))
        height = max(int(height), int(min_h))

        fix_point_names = self._FIX_POINTS.get(direction, "NORTH_WEST")

        try:
            fix_point = None

            for name in fix_point_names.split("_"):
                point = getattr(FixPoint, name)
                fix_point = point if fix_point is None else (fix_point | point)

            window.resize(width, height, fix_point=fix_point)

        except Exception:
            # Older pywebview versions (or a platform backend that doesn't
            # support fix_point) still get a working, if less precise, resize.
            window.resize(width, height)

        return {
            "success": True,
            "width": width,
            "height": height,
        }

    # ------------------------------------------------------------
    # Controller
    # ------------------------------------------------------------

    def get_controller_state(self):
        """Return controller state without allowing hot-plug errors to escape.

        ControllerManager handles SDL hot-plugging internally. This extra
        guard protects the pywebview bridge if an unexpected native error
        occurs outside the normal pygame.error path.
        """
        try:
            return controller.poll()
        except Exception:
            return {
                "connected": False,
                "name": None,
                "pressed": [],
                "nav": None,
            }


api = GameLibraryAPI()


def resource_path(*parts):
    """
    Get the path to bundled application resources.

    Development:
        Uses the project directory.

    PyInstaller:
        Uses PyInstaller's temporary/bundled resource directory.
    """
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent

    return base.joinpath(*parts)


FRONTEND_DIR = resource_path("frontend")


app = FastAPI(title="Game Library")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/games/launch")
def launch_game(payload: dict):
    platform = str(payload.get("platform", ""))
    game_id = str(payload.get("id", ""))

    game = next(
        (
            item
            for item in get_all_games()
            if item["platform"] == platform
            and str(item["id"]) == game_id
        ),
        None,
    )

    if not game:
        return {
            "success": False,
            "message": "Game not found",
        }

    launch_type = game.get("launch_type", "uri")

    try:
        # ---------------------------------
        # Direct EXE launch
        # ---------------------------------
        if launch_type == "exe":
            exe_path = game.get("exe_path")

            if not exe_path or not Path(exe_path).is_file():
                return {
                    "success": False,
                    "message": "Game EXE no longer exists",
                }

            subprocess.Popen(
                [exe_path],
                cwd=str(Path(exe_path).parent),
            )

            return {
                "success": True,
            }

        # ---------------------------------
        # Battle.net launch
        # ---------------------------------
        if launch_type == "battlenet":
            battlenet_exe = game.get("exe_path")
            launch_code = game.get("launch_code")

            if (
                not battlenet_exe
                or not Path(battlenet_exe).is_file()
            ):
                return {
                    "success": False,
                    "message": "Battle.net executable not found",
                }

            if not launch_code:
                return {
                    "success": False,
                    "message": "Battle.net product code missing",
                }

            subprocess.Popen(
                [
                    battlenet_exe,
                    f"--exec=launch {launch_code}",
                ],
                cwd=str(Path(battlenet_exe).parent),
            )

            return {
                "success": True,
            }

        return {
            "success": False,
            "message": "Unsupported launch type",
        }

    except Exception as exc:
        return {
            "success": False,
            "message": str(exc),
        }


@app.get("/api/games")
def games():
    result = []

    favorite_keys = set(get_favorites())

    for game in get_all_games():
        platform = game["platform"]
        game_id = game["id"]

        entry = {
            "platform": platform,
            "id": game_id,
            "name": game["name"],
            "launch_uri": game.get("launch_uri"),
            "launch_type": game.get("launch_type", "uri"),
            "launch_code": game.get("launch_code"),
            "exe_path": game.get("exe_path"),
            "has_image": has_local_image(
                platform,
                game_id,
            ),
            "image_url": local_image_url(
                platform,
                game_id,
            ),
            "is_favorite": f"{platform}:{game_id}" in favorite_keys,
        }

        result.append(entry)

    return {
        "games": result,
    }


@app.post("/api/games/{platform}/{game_id}/image")
def game_image(
    platform: str,
    game_id: str,
):
    # Find the game's real display name so Steam fallback
    # search can use it.
    game = next(
        (
            item
            for item in get_all_games()
            if item["platform"] == platform
            and str(item["id"]) == str(game_id)
        ),
        None,
    )

    if not game:
        return {
            "success": False,
            "message": "Game not found",
        }

    path = resolve_image(
        platform,
        game_id,
        game["name"],
    )

    if not path:
        return {
            "success": False,
            "message": "Image not found",
        }

    return {
        "success": True,
        "image_url": local_image_url(
            platform,
            game_id,
        ),
    }


@app.delete("/api/games/custom/{game_id}")
def delete_custom_game(game_id: str):
    """
    Remove a game imported through "Custom". Steam/Epic/GOG/etc.
    games are just scanned from the real launchers and can't be
    deleted from here.
    """
    removed = remove_game(game_id)

    if not removed:
        return {
            "success": False,
            "message": "Game not found",
        }

    return {
        "success": True,
    }


@app.get("/api/favorites")
def favorites():
    return {
        "favorites": get_favorites(),
    }


@app.post("/api/favorites/toggle")
def favorites_toggle(payload: dict):
    platform = str(payload.get("platform", ""))
    game_id = str(payload.get("id", ""))

    if not platform or not game_id:
        return {
            "success": False,
            "message": "platform and id are required",
        }

    is_favorite = toggle_favorite(platform, game_id)

    return {
        "success": True,
        "is_favorite": is_favorite,
    }


# Cached box art:
# /images/<platform>/<id>.jpg
app.mount(
    "/images",
    StaticFiles(directory=IMAGE_FOLDER),
    name="images",
)


# Frontend assets:
# /static/...
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)


# User-picked wallpaper image:
# /wallpaper/custom.<ext>
app.mount(
    "/wallpaper",
    StaticFiles(directory=WALLPAPER_FOLDER),
    name="wallpaper",
)


@app.get("/")
def index():
    return FileResponse(
        FRONTEND_DIR / "index.html"
    )
