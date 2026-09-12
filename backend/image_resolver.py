"""Cross-platform box-art resolver.

Resolution order
----------------

                    ┌─────────────────┐
                    │   Local Cache    │
                    └────────┬────────┘
                             │ miss
                    ┌────────▼────────┐
                    │ Native Source   │
                    │ Steam / GOG     │
                    └────────┬────────┘
                             │ miss
                    ┌────────▼────────┐
                    │ Steam Search     │
                    │ Exact-name match │
                    └────────┬────────┘
                             │ miss
                    ┌────────▼────────┐
                    │ Steam HTML      │
                    │ Last fallback   │
                    └────────┬────────┘
                             │ miss
                    ┌────────▼────────┐
                    │     None        │
                    │ Frontend tile   │
                    └─────────────────┘

Steam:
    Uses Steam's public appdetails API and CDN.

GOG:
    Uses GOG's public product API.

Epic / Ubisoft:
    Search Steam by game name and borrow the Steam artwork.

All successful images are cached under:

    images/<platform>/<game_id>.jpg

The images folder intentionally lives outside backend/
so uvicorn --reload does not restart whenever an image
is downloaded.
"""

import os
import sys
from pathlib import Path as FilePath
import re
import tempfile
from urllib.parse import quote
from difflib import SequenceMatcher
from urllib.parse import quote_plus
from anyio import Path
import requests

def resolve_generic_image(game_name, platform, game_id):
    """
    Generic artwork resolver for games that don't have a native
    image source.

    Uses Steam's public store search as an internet artwork index.
    """
    if not game_name:
        return None

    output_dir = IMAGE_FOLDER / platform
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{game_id}.jpg"

    if output_path.is_file() and output_path.stat().st_size > 0:
        return output_path

    try:
        url = (
            "https://store.steampowered.com/api/storesearch/"
            f"?term={quote_plus(game_name)}"
            "&l=english&cc=us"
        )

        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "GameLibrary/1.0"
            },
        )

        response.raise_for_status()

        results = response.json().get("items", [])

    except Exception:
        return None

    if not results:
        return None

    def normalize(value):
        value = str(value).lower()

        replacements = [
            "™",
            "®",
            "©",
            ":",
            "-",
            "_",
            "'",
            '"',
        ]

        for char in replacements:
            value = value.replace(char, " ")

        return " ".join(value.split())

    wanted = normalize(game_name)

    candidates = []

    for item in results:
        if item.get("type") != "app":
            continue

        name = item.get("name", "")

        if not name:
            continue

        score = SequenceMatcher(
            None,
            wanted,
            normalize(name),
        ).ratio()

        # Exact name gets a very strong score.
        if normalize(name) == wanted:
            score = 1.0

        candidates.append(
            (
                score,
                int(item["id"]),
                name,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    score, app_id, matched_name = candidates[0]

    # Avoid obviously bad matches.
    if score < 0.45:
        return None

    image_urls = [
        f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg",
        f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg",
    ]

    for image_url in image_urls:
        try:
            image_response = requests.get(
                image_url,
                timeout=15,
                headers={
                    "User-Agent": "GameLibrary/1.0"
                },
            )

            image_response.raise_for_status()

            content = image_response.content

            if len(content) < 1000:
                continue

            temp_path = output_path.with_suffix(".tmp")

            temp_path.write_bytes(content)

            os.replace(
                temp_path,
                output_path,
            )

            return output_path

        except Exception:
            continue

    return None
# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

IMAGE_FOLDER = os.path.join(
    PROJECT_ROOT,
    "images"
)

os.makedirs(
    IMAGE_FOLDER,
    exist_ok=True
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/153.0.0.0 "
        "Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}


TIMEOUT = 10


# ============================================================================
# FILESYSTEM HELPERS
# ============================================================================

def get_data_folder():
    if sys.platform == "win32":
        base = FilePath(os.environ.get("LOCALAPPDATA", str(FilePath.home())))
        folder = base / "GameLibrary"
    else:
        folder = FilePath.home() / ".gamelibrary"

    folder.mkdir(parents=True, exist_ok=True)
    return folder


DATA_FOLDER = get_data_folder()

IMAGE_FOLDER = DATA_FOLDER / "images"
IMAGE_FOLDER.mkdir(parents=True, exist_ok=True)

PROJECT_ROOT = FilePath(__file__).resolve().parent

def _safe_filename(value):
    """Make a value safe to use as a filename."""

    value = str(value)

    value = re.sub(
        r'[<>:"/\\|?*\x00-\x1f]',
        "_",
        value
    )

    value = value.strip()

    return value or "unknown"


def _local_path(platform, game_id):
    """Return the local cache path."""

    platform = _safe_filename(platform)
    game_id = _safe_filename(game_id)

    folder = os.path.join(
        IMAGE_FOLDER,
        platform
    )

    os.makedirs(
        folder,
        exist_ok=True
    )

    return os.path.join(
        folder,
        f"{game_id}.jpg"
    )


def local_image_url(platform, game_id):
    """Return the frontend URL for the cached image."""

    platform = _safe_filename(platform)
    game_id = _safe_filename(game_id)

    return (
        f"/images/"
        f"{quote(platform, safe='')}/"
        f"{quote(game_id, safe='')}.jpg"
    )


def has_local_image(platform, game_id):
    """Check whether an image already exists locally."""

    return os.path.isfile(
        _local_path(
            platform,
            game_id
        )
    )


# ============================================================================
# HTTP HELPERS
# ============================================================================

def _download_bytes(url):
    """Download an image and return its bytes.

    Returns None when the request fails or the response is not an image.
    """

    if not url:
        return None

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True
        )

        response.raise_for_status()

    except requests.RequestException:
        return None

    content_type = (
        response.headers
        .get("content-type", "")
        .lower()
    )

    # Some CDN responses don't always have a perfect content-type.
    # Therefore don't reject an otherwise valid response solely because
    # the header is missing.
    if content_type and not content_type.startswith("image/"):
        return None

    if not response.content:
        return None

    return response.content


def _save_image(local_path, image_bytes):
    """Atomically save image bytes to disk."""

    if not image_bytes:
        return False

    folder = os.path.dirname(local_path)

    os.makedirs(
        folder,
        exist_ok=True
    )

    temp_path = None

    try:

        fd, temp_path = tempfile.mkstemp(
            prefix=".image_",
            suffix=".tmp",
            dir=folder
        )

        with os.fdopen(
            fd,
            "wb"
        ) as f:
            f.write(image_bytes)

            f.flush()

            try:
                os.fsync(f.fileno())
            except OSError:
                pass

        os.replace(
            temp_path,
            local_path
        )

        return True

    except OSError:

        if temp_path:

            try:
                os.remove(temp_path)
            except OSError:
                pass

        return False


# ============================================================================
# NAME NORMALIZATION
# ============================================================================

def _normalize_name(name):
    """Normalize a game name for comparison."""

    if not name:
        return ""

    name = str(name).lower().strip()

    # Replace punctuation with spaces.
    name = re.sub(
        r"[^a-z0-9]+",
        " ",
        name
    )

    # Remove duplicate whitespace.
    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name.strip()


def _name_similarity(a, b):
    """Return a similarity score between two game names."""

    a = _normalize_name(a)
    b = _normalize_name(b)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    # One contains the other.
    if a in b or b in a:
        return 0.92

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


# ============================================================================
# STEAM
# ============================================================================

def _steam_appdetails(app_id):
    """Get Steam app details for an App ID."""

    if not app_id:
        return None

    try:

        response = requests.get(
            "https://store.steampowered.com/api/appdetails/",
            params={
                "appids": app_id,
                "cc": "US",
                "l": "english",
            },
            headers=HEADERS,
            timeout=TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

    except (
        requests.RequestException,
        ValueError
    ):
        return None

    entry = data.get(
        str(app_id)
    )

    if not isinstance(entry, dict):
        return None

    if not entry.get("success"):
        return None

    return entry.get("data")


def _steam_appdetails_image(app_id):
    """Get the official header image from Steam's appdetails API."""

    data = _steam_appdetails(
        app_id
    )

    if not data:
        return None

    image_url = data.get(
        "header_image"
    )

    if not image_url:
        return None

    return _download_bytes(
        image_url
    )


def _native_steam(game_id, _name=None):
    """Fetch Steam artwork.

    Tries Steam's official appdetails API first, followed by several
    CDN URL variants.

    This is more reliable than relying on a single CDN URL.
    """

    if not game_id:
        return None

    # ------------------------------------------------------------
    # 1. Official Steam appdetails API
    # ------------------------------------------------------------

    image_bytes = _steam_appdetails_image(
        game_id
    )

    if image_bytes:
        return image_bytes

    # ------------------------------------------------------------
    # 2. Steam CDN variants
    # ------------------------------------------------------------

    app_id = str(
        game_id
    ).strip()

    urls = [

        # Main header artwork.
        f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg",

        # Steam's standard static CDN.
        f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg",

        # Alternate Steam static domain.
        f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg",

        # Vertical library artwork.
        f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_600x900_2x.jpg",

        # Older library artwork.
        f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/library_600x900.jpg",

        # Capsule fallback.
        f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/capsule_616x353.jpg",
    ]

    for url in urls:

        image_bytes = _download_bytes(
            url
        )

        if image_bytes:
            return image_bytes

    return None


# ============================================================================
# GOG
# ============================================================================

def _native_gog(game_id, _name=None):
    """Fetch artwork from the GOG product API."""

    if not game_id:
        return None

    try:

        response = requests.get(
            f"https://api.gog.com/products/{game_id}",
            headers=HEADERS,
            timeout=TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

    except (
        requests.RequestException,
        ValueError
    ):
        return None

    images = data.get(
        "images",
        {}
    )

    if not isinstance(
        images,
        dict
    ):
        return None

    image_url = (
        images.get("background")
        or images.get("logo2x")
        or images.get("logo")
    )

    if not image_url:
        return None

    if image_url.startswith("//"):
        image_url = (
            "https:"
            + image_url
        )

    return _download_bytes(
        image_url
    )


# ============================================================================
# NATIVE SOURCE REGISTRY
# ============================================================================

NATIVE_SOURCES = {
    "steam": _native_steam,
    "gog": _native_gog,
}


# ============================================================================
# STEAM SEARCH
# ============================================================================

def _steam_search(name):
    """Search Steam and return the result list."""

    if not name:
        return []

    try:

        response = requests.get(
            "https://store.steampowered.com/api/storesearch/",
            params={
                "term": name,
                "l": "english",
                "cc": "US",
            },
            headers=HEADERS,
            timeout=TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

    except (
        requests.RequestException,
        ValueError
    ):
        return []

    results = data.get(
        "items",
        []
    )

    if not isinstance(
        results,
        list
    ):
        return []

    return results


def _pick_best_steam_result(results, name):
    """Pick the Steam result that best matches the requested game name.

    The old resolver always used results[0].

    That can break for games with short/common names.

    This version scores every result and prefers an exact title match.
    """

    if not results:
        return None

    requested = _normalize_name(
        name
    )

    best_result = None
    best_score = -1.0

    for result in results:

        if not isinstance(
            result,
            dict
        ):
            continue

        title = result.get(
            "name"
        )

        app_id = result.get(
            "id"
        )

        if not title or not app_id:
            continue

        normalized_title = _normalize_name(
            title
        )

        # Exact match gets maximum priority.
        if normalized_title == requested:
            score = 1.0

        else:
            score = _name_similarity(
                requested,
                title
            )

        if score > best_score:

            best_score = score

            best_result = result

    # Don't accept a completely unrelated Steam game.
    if best_result is None:
        return None

    if best_score < 0.55:
        return None

    return best_result


def _steam_search_fallback(_game_id, name):
    """Find Steam artwork using the game name."""

    if not name:
        return None

    results = _steam_search(
        name
    )

    best = _pick_best_steam_result(
        results,
        name
    )

    if not best:
        return None

    matched_app_id = best.get(
        "id"
    )

    if not matched_app_id:
        return None

    # Use the exact matched Steam App ID.
    return _native_steam(
        matched_app_id,
        best.get("name")
    )


# ============================================================================
# OLD STEAM HTML FALLBACK
# ============================================================================

def _steam_html_fallback(game_id):
    """Last-resort fallback using the Steam store page.

    This intentionally exists only as a fallback.

    The resolver normally uses Steam's API/CDN first, but this protects
    older/special Steam games where the CDN/API route doesn't return
    artwork even though the Steam page still exposes it.
    """

    if not game_id:
        return None

    url = (
        f"https://store.steampowered.com/app/"
        f"{game_id}/"
    )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True
        )

        response.raise_for_status()

        html = response.text

    except requests.RequestException:
        return None

    # ------------------------------------------------------------
    # First try the old Steam header image class.
    # ------------------------------------------------------------

    patterns = [

        # Current/old game_header_image_full structure.
        r'class=["\'][^"\']*game_header_image_full[^"\']*["\'][^>]*>'
        r'.*?src=["\']([^"\']+)["\']',

        # Generic header image.
        r'class=["\'][^"\']*game_header_image[^"\']*["\'][^>]*>'
        r'.*?src=["\']([^"\']+)["\']',

        # Direct header.jpg reference.
        r'(https?://[^"\']+/steam/apps/\d+/header\.jpg)',

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            flags=re.IGNORECASE | re.DOTALL
        )

        if not match:
            continue

        image_url = match.group(
            1
        )

        # HTML escaping.
        image_url = (
            image_url
            .replace("&amp;", "&")
        )

        image_bytes = _download_bytes(
            image_url
        )

        if image_bytes:
            return image_bytes

    return None


# ============================================================================
# MAIN RESOLVER
# ============================================================================

def resolve_image(platform, game_id, name=None):
    """Resolve and cache artwork.

    Resolution order:

        1. Local cache
        2. Native source
        3. Steam name search
        4. Steam HTML fallback
        5. None

    Returns the local filesystem path when successful.
    """
    if platform in {"custom", "ea", "battlenet"}:
        return resolve_generic_image(
            name,
            platform,
            game_id,
        )
    platform = str(
        platform
    ).lower().strip()

    local_path = _local_path(
        platform,
        game_id
    )

    # ------------------------------------------------------------
    # 1. CACHE
    # ------------------------------------------------------------

    if os.path.isfile(
        local_path
    ):

        # Don't touch/re-download cached images.
        return local_path

    image_bytes = None

    # ------------------------------------------------------------
    # 2. NATIVE SOURCE
    # ------------------------------------------------------------

    native = NATIVE_SOURCES.get(
        platform
    )

    if native:

        image_bytes = native(
            game_id,
            name
        )

    # ------------------------------------------------------------
    # 3. STEAM SEARCH FALLBACK
    # ------------------------------------------------------------

    if not image_bytes:

        image_bytes = _steam_search_fallback(
            game_id,
            name
        )

    # ------------------------------------------------------------
    # 4. STEAM HTML FALLBACK
    # ------------------------------------------------------------

    if not image_bytes and platform == "steam":

        image_bytes = _steam_html_fallback(
            game_id
        )

    # ------------------------------------------------------------
    # 5. NOTHING FOUND
    # ------------------------------------------------------------

    if not image_bytes:
        return None

    # ------------------------------------------------------------
    # 6. CACHE
    # ------------------------------------------------------------

    if not _save_image(
        local_path,
        image_bytes
    ):
        return None

    return local_path


# ============================================================================
# STEAM COMPATIBILITY FUNCTION
# ============================================================================

def download_game_image(app_id, name=None):
    """Compatibility wrapper for old Steam code.

    Existing code can continue doing:

        download_game_image(app_id)

    or:

        download_game_image(app_id, game_name)
    """

    return resolve_image(
        "steam",
        app_id,
        name
    )
