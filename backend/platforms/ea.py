import os
import re
import winreg
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET


EA_REGISTRY_PATHS = [
    r"SOFTWARE\EA Games",
    r"SOFTWARE\Origin Games",
]


def _read_value(key, names):
    for name in names:
        try:
            value, _ = winreg.QueryValueEx(key, name)
            if value:
                return str(value)
        except OSError:
            pass
    return None


def _read_installer_data(install_dir):
    """
    Try to obtain the real EA game title and content IDs from
    __Installer/installerdata.xml.
    """
    xml_path = Path(install_dir) / "__Installer" / "installerdata.xml"

    if not xml_path.exists():
        return None, []

    try:
        root = ET.parse(xml_path).getroot()
    except (ET.ParseError, OSError):
        return None, []

    title = None
    content_ids = []

    # Find gameTitle elements.
    for element in root.iter():
        tag = element.tag.lower().split("}")[-1]

        if tag == "gametitle":
            locale = element.attrib.get("locale", "")
            text = (element.text or "").strip()

            if text and (
                locale.lower() in ("en_us", "en-us", "en")
                or title is None
            ):
                title = text

        elif tag == "contentid":
            text = (element.text or "").strip()
            if text:
                content_ids.append(text)

    # Some installerdata files store IDs as attributes.
    for element in root.iter():
        for key, value in element.attrib.items():
            if key.lower() in ("contentid", "contentids"):
                for item in re.split(r"[,;\s]+", value):
                    item = item.strip()
                    if item:
                        content_ids.append(item)

    # Remove duplicates while preserving order.
    content_ids = list(dict.fromkeys(content_ids))

    return title, content_ids


def _scan_registry(registry_path, wow_flag):
    games = []

    try:
        root = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            registry_path,
            0,
            winreg.KEY_READ | wow_flag,
        )
    except OSError:
        return games

    try:
        index = 0

        while True:
            try:
                subkey_name = winreg.EnumKey(root, index)
                index += 1
            except OSError:
                break

            try:
                subkey = winreg.OpenKey(root, subkey_name)
            except OSError:
                continue

            try:
                install_dir = _read_value(
                    subkey,
                    [
                        "Install Dir",
                        "InstallDir",
                        "Install Location",
                        "InstallLocation",
                    ],
                )

                if not install_dir:
                    continue

                install_dir = os.path.expandvars(install_dir).strip('"')
                install_path = Path(install_dir)

                if not install_path.is_dir():
                    continue

                display_name = _read_value(
                    subkey,
                    [
                        "DisplayName",
                        "Display Name",
                        "Name",
                    ],
                )

                xml_title, content_ids = _read_installer_data(install_path)

                name = (
                    xml_title
                    or display_name
                    or subkey_name
                    or install_path.name
                )

                # EA's launcher URI expects offer IDs. installerdata.xml
                # can contain multiple content IDs for one game.
                offer_ids = content_ids or [subkey_name]

                launch_uri = (
                    "origin2://game/launch/?offerIds="
                    + quote(",".join(offer_ids))
                    + "&autoDownload=1"
                )

                games.append(
                    {
                        "platform": "ea",
                        "id": subkey_name,
                        "name": name,
                        "launch_uri": launch_uri,
                        "launch_type": "uri",
                        "exe_path": None,
                        "install_path": str(install_path),
                    }
                )

            finally:
                try:
                    winreg.CloseKey(subkey)
                except Exception:
                    pass

    finally:
        winreg.CloseKey(root)

    return games


def scan():
    if os.name != "nt":
        return []

    games = []
    seen = set()

    wow_flags = [
        0,
        getattr(winreg, "KEY_WOW64_64KEY", 0),
        getattr(winreg, "KEY_WOW64_32KEY", 0),
    ]

    for registry_path in EA_REGISTRY_PATHS:
        for wow_flag in wow_flags:
            for game in _scan_registry(registry_path, wow_flag):
                install_path = os.path.normcase(
                    os.path.normpath(game["install_path"])
                )

                if install_path in seen:
                    continue

                seen.add(install_path)
                games.append(game)

    return games