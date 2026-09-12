import os
from pathlib import Path


PRODUCT_NAMES = {
    "s1": "StarCraft",
    "s2": "StarCraft II",
    "wow": "World of Warcraft",
    "wow_classic": "World of Warcraft Classic",
    "wow_classic_era": "World of Warcraft Classic Era",
    "pro": "Overwatch 2",
    "w1": "Warcraft: Orcs & Humans",
    "w1r": "Warcraft I: Remastered",
    "w2bn": "Warcraft II: Battle.net Edition",
    "w2r": "Warcraft II: Remastered",
    "w3": "Warcraft III",
    "gryphon": "Warcraft Rumble",
    "hsb": "Hearthstone",
    "hero": "Heroes of the Storm",
    "d3": "Diablo III",
    "d3cn": "Diablo III",
    "fenris": "Diablo IV",
    "osi": "Diablo II: Resurrected",
    "d2": "Diablo II",
    "viper": "Call of Duty: Black Ops 4",
    "odin": "Call of Duty: Modern Warfare",
    "lazarus": "Call of Duty: MW2 Campaign Remastered",
    "zeus": "Call of Duty: Black Ops Cold War",
    "auks": "Call of Duty: Modern Warfare II",
    "codhq": "Call of Duty HQ",
    "fore": "Call of Duty: Vanguard",
    "rtro": "Blizzard Arcade Collection",
    "wlby": "Crash Bandicoot 4: It's About Time",
    "anbs": "Diablo Immortal",
}


PRODUCT_DB = (
    Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
    / "Battle.net"
    / "Agent"
    / "product.db"
)


def _read_varint(data, offset):
    value = 0
    shift = 0

    while offset < len(data):
        byte = data[offset]
        offset += 1

        value |= (byte & 0x7F) << shift

        if not byte & 0x80:
            return value, offset

        shift += 7

        if shift > 70:
            raise ValueError("Invalid protobuf varint")

    raise ValueError("Unexpected end of protobuf")


def _parse_message(data):
    """
    Very small generic protobuf decoder.

    Returns:
        {
            field_number: [values...]
        }

    We only need:
        ProductDb.product_installs
        ProductInstall.product_code
        ProductInstall.settings.install_path
        ProductInstall.cached_product_state.base_product_state.installed
    """
    fields = {}
    offset = 0

    while offset < len(data):
        key, offset = _read_varint(data, offset)

        field_number = key >> 3
        wire_type = key & 7

        if field_number == 0:
            break

        if wire_type == 0:
            value, offset = _read_varint(data, offset)

        elif wire_type == 1:
            if offset + 8 > len(data):
                break

            value = data[offset:offset + 8]
            offset += 8

        elif wire_type == 2:
            length, offset = _read_varint(data, offset)

            if offset + length > len(data):
                break

            value = data[offset:offset + length]
            offset += length

        elif wire_type == 5:
            if offset + 4 > len(data):
                break

            value = data[offset:offset + 4]
            offset += 4

        else:
            # Groups / unsupported wire types.
            break

        fields.setdefault(field_number, []).append(value)

    return fields


def _decode_string(value):
    if not isinstance(value, bytes):
        return None

    try:
        return value.decode("utf-8", errors="ignore").strip("\x00")
    except Exception:
        return None


def _decode_product_install(data):
    fields = _parse_message(data)

    product_code = None
    install_path = None
    installed = True

    # ProductInstall.product_code = field 2
    if 2 in fields:
        product_code = _decode_string(fields[2][0])

    # ProductInstall.settings = field 3
    if 3 in fields:
        settings = _parse_message(fields[3][0])

        # UserSettings.install_path = field 1
        if 1 in settings:
            install_path = _decode_string(settings[1][0])

    # ProductInstall.cached_product_state = field 4
    if 4 in fields:
        cached_state = _parse_message(fields[4][0])

        # CachedProductState.base_product_state = field 1
        if 1 in cached_state:
            base_state = _parse_message(cached_state[1][0])

            # BaseProductState.installed = field 1
            if 1 in base_state:
                installed = bool(base_state[1][0])

    return product_code, install_path, installed


def _find_product_installs(data):
    database = _parse_message(data)

    # ProductDb.product_installs = repeated field 1.
    return database.get(1, [])


def _find_battlenet_exe():
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "Battle.net"
        / "Battle.net.exe",

        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "Battle.net"
        / "Battle.net.exe",

        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "Battle.net"
        / "Battle.net Launcher.exe",
    ]

    for path in candidates:
        if path.is_file():
            return str(path)

    return None


def scan():
    if os.name != "nt":
        return []

    if not PRODUCT_DB.exists():
        return []

    try:
        data = PRODUCT_DB.read_bytes()
    except OSError:
        return []

    battlenet_exe = _find_battlenet_exe()

    if not battlenet_exe:
        return []

    games = []
    seen = set()

    try:
        product_installs = _find_product_installs(data)
    except Exception:
        return []

    for product_install in product_installs:
        try:
            product_code, install_path, installed = _decode_product_install(
                product_install
            )
        except Exception:
            continue

        if not product_code:
            continue

        if product_code.lower() in {"agent", "bna"}:
            continue

        if not installed:
            continue

        if not install_path:
            continue

        install_path = os.path.expandvars(install_path).strip('"')
        install_dir = Path(install_path)

        if not install_dir.is_dir():
            continue

        key = (
            product_code.lower(),
            os.path.normcase(os.path.normpath(str(install_dir))),
        )

        if key in seen:
            continue

        seen.add(key)

        name = PRODUCT_NAMES.get(
            product_code,
            product_code,
        )

        games.append(
            {
                "platform": "battlenet",
                "id": product_code,
                "name": name,
                "launch_uri": None,
                "launch_type": "battlenet",
                "launch_code": product_code,
                "exe_path": battlenet_exe,
                "install_path": str(install_dir),
            }
        )

    return games