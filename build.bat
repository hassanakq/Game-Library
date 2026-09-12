@echo off
REM Build the GameLibrary.exe using the spec file (which bundles pygame /
REM pywebview's native files correctly -- this is what fixes the controller).
py -m PyInstaller --noconfirm --clean GameLibrary.spec
