def _lookup_name(winreg, game_id):
    """Ubisoft's install key doesn't carry a display name, but its uninstall
    entry does — look it up there, and fall back to a generic label if
    that entry is missing for some reason."""
    key_path = (
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion"
        rf"\Uninstall\Uplay Install {game_id}"
    )
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            return winreg.QueryValueEx(key, "DisplayName")[0]
    except OSError:
        return None


def scan():
    """Return games in the platforms.scan() shape: [{platform, id, name, launch_uri}]."""
    try:
        import winreg
    except ImportError:
        return []

    try:
        installs = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Ubisoft\Launcher\Installs",
        )
    except OSError:
        return []

    games = []
    with installs:
        index = 0
        while True:
            try:
                game_id = winreg.EnumKey(installs, index)
            except OSError:
                break
            index += 1

            name = _lookup_name(winreg, game_id) or f"Ubisoft game {game_id}"

            games.append({
                "platform": "ubisoft",
                "id": game_id,
                "name": name,
                "launch_uri": f"uplay://launch/{game_id}/0",
            })

    return games
