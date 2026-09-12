def scan():
    """Return games in the platforms.scan() shape: [{platform, id, name, launch_uri}].

    GOG Galaxy registers every installed game under this registry key.
    On non-Windows systems, or if Galaxy was never installed, this
    just comes back empty.
    """
    try:
        import winreg
    except ImportError:
        return []

    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\GOG.com\Games")
    except OSError:
        try:
            root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\GOG.com\Games")
        except OSError:
            return []

    games = []
    with root:
        index = 0
        while True:
            try:
                game_id = winreg.EnumKey(root, index)
            except OSError:
                break
            index += 1

            try:
                with winreg.OpenKey(root, game_id) as key:
                    name = winreg.QueryValueEx(key, "gameName")[0]
            except OSError:
                continue

            games.append({
                "platform": "gog",
                "id": game_id,
                "name": name,
                # Handed off to the Galaxy client, which owns the actual launch.
                "launch_uri": f"goggalaxy://openGameView/{game_id}",
            })

    return games
