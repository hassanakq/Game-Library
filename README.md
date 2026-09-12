# 🎮 GameLibrary

### Your games. One library. One place.

A modern Windows desktop game library for **browsing, organizing, and launching your games** through a clean and unified interface.

<p align="center">

<a href="https://github.com/hassanakq/Game-Library/releases/latest/download/GameLibrary.exe">
<img src="https://img.shields.io/badge/Download-GameLibrary.exe-2ea44f?style=for-the-badge&logo=windows" alt="Download GameLibrary">
</a>

<a href="https://github.com/hassanakq/Game-Library/releases/latest">
<img src="https://img.shields.io/github/v/release/hassanakq/Game-Library?style=for-the-badge&logo=github" alt="Latest Release">
</a>

<a href="https://github.com/hassanakq/Game-Library/stargazers">
<img src="https://img.shields.io/github/stars/hassanakq/Game-Library?style=for-the-badge&logo=github" alt="GitHub Stars">
</a>

</p>

---

## ✨ Overview

**GameLibrary** is a Windows desktop application built to bring your game collection together in one place.

Instead of searching through different folders, launchers, and shortcuts, GameLibrary provides a single interface where you can **browse your games, view their artwork, manage your collection, and launch them directly**.

The application combines a modern web-based interface with a Python desktop backend to provide a lightweight and flexible gaming library.

---

## 🚀 Features

<table>
<tr>
<td width="50%">

### 🎮 Game Library

* Browse your game collection
* Search and filter games
* View game artwork
* Organize your collection
* Launch games directly

</td>
<td width="50%">

### 🖼️ Game Artwork

* Automatic game artwork
* Local image caching
* Faster loading after first retrieval
* Custom game artwork support

</td>
</tr>

<tr>
<td width="50%">

### 🎛️ Controller Support

* Game controller integration
* Controller-friendly interaction
* Designed for a more console-like experience

</td>
<td width="50%">

### 🔗 Game Sources

* Steam game support
* Custom game importing
* Local game executable support
* Flexible game launching

</td>
</tr>
</table>

---

## 🖥️ Interface

> Screenshots coming soon.

<!--
Add screenshots here:

<p align="center">
  <img src="screenshots/library.png" width="800" alt="GameLibrary Interface">
</p>
-->

---

## 📥 Download

### Windows

<p align="center">

<a href="https://github.com/hassanakq/Game-Library/releases/latest/download/GameLibrary.exe">
<img src="https://img.shields.io/badge/Download-GameLibrary.exe-2ea44f?style=for-the-badge&logo=windows" alt="Download GameLibrary for Windows">
</a>

</p>

Download the latest Windows executable directly from GitHub Releases.

**No Python installation is required.**

### Installation

1. Download `GameLibrary.exe`.
2. Place it anywhere on your computer.
3. Run `GameLibrary.exe`.
4. Start adding and launching your games.

---

## ⚠️ Windows SmartScreen

The application is currently **not digitally signed**, so Windows may display:

> **Windows protected your PC**

This happens because Windows cannot verify the publisher of the executable.

If you downloaded the application from this repository and trust the source:

**More info → Run anyway**

The warning is related to code signing and does not mean that the application failed to build.

---

## 🛠️ Built With

| Technology      | Purpose                       |
| --------------- | ----------------------------- |
| **Python**      | Application backend           |
| **PyWebView**   | Desktop application window    |
| **Pygame**      | Controller and input handling |
| **FastAPI**     | Backend API                   |
| **HTML**        | Frontend structure            |
| **CSS**         | Interface styling             |
| **JavaScript**  | Frontend functionality        |
| **PyInstaller** | Windows executable packaging  |

---

## 🏗️ Architecture

GameLibrary combines a Python backend with a web-based frontend:

```text
                    GameLibrary
                         │
              ┌──────────┴──────────┐
              │                     │
          Frontend                Backend
              │                     │
      HTML / CSS / JS            Python
              │                     │
              └──────────┬──────────┘
                         │
                     PyWebView
                         │
                  Windows Desktop
                         │
             ┌───────────┴───────────┐
             │                       │
          Pygame                 FastAPI
             │                       │
       Controller Input         Game / Image API
```

---

## 📂 Project Structure

```text
Game-Library/
│
├── backend/
│   ├── ...
│   └── requirements.txt
│
├── frontend/
│   ├── ...
│   └── index.html
│
├── GameLibrary.spec
├── build.bat
├── run_app.py
├── app.ico
└── README.md
```

---

## 🔨 Build From Source

### 1. Clone the repository

```bash
git clone https://github.com/hassanakq/Game-Library.git
cd Game-Library
```

### 2. Install dependencies

```bash
python -m pip install -r backend/requirements.txt
python -m pip install pyinstaller
```

### 3. Build

```bash
python -m PyInstaller --noconfirm --clean GameLibrary.spec
```

Or simply run:

```text
build.bat
```

The final executable will be generated at:

```text
dist/GameLibrary.exe
```

---

## ⚙️ Automated Builds

GameLibrary uses **GitHub Actions** to automatically build the Windows executable.

When changes are pushed to the `main` branch:

```text
Push
 │
 ▼
GitHub Actions
 │
 ▼
Python 3.11
 │
 ▼
PyInstaller
 │
 ▼
GameLibrary.exe
 │
 ▼
GitHub Release
```

Each successful build can be published as a new GitHub Release.

---

## 📦 Releases

Get the latest version:

<p align="center">

<a href="https://github.com/hassanakq/Game-Library/releases/latest">
<img src="https://img.shields.io/badge/View%20Latest%20Release-181717?style=for-the-badge&logo=github" alt="View Latest Release">
</a>

</p>

---

## 🗺️ Roadmap

Some ideas for future development:

* [ ] Improved game metadata
* [ ] More game platforms
* [ ] Better controller navigation
* [ ] Game categories and filters
* [ ] Favorites
* [ ] Playtime tracking
* [ ] Improved custom game importing
* [ ] Automatic updates
* [ ] Digitally signed Windows releases

---

## 👨‍💻 Author

### Hassan Ali

Computer Science graduate and software developer.

GameLibrary is an independent project created to explore **desktop application development, game library management, web technologies, and Python integration**.

---

## ⭐ Support

If you find GameLibrary useful, consider giving the repository a ⭐ on GitHub.

<p align="center">

<a href="https://github.com/hassanakq/Game-Library">
<img src="https://img.shields.io/badge/⭐%20Star%20the%20Repository-181717?style=for-the-badge&logo=github" alt="Star the Repository">
</a>

</p>

---

## 📄 License

This project currently does not specify an open-source license.

If you intend to allow others to modify, distribute, or reuse the source code, an appropriate license should be added.
