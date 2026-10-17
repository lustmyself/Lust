# 🌹 Lust - Effortless Skin Changer for LoL

<div align="center">

  <img src="./assets/icon.png" alt="Lust Icon" width="128" height="128">

[![Installer](https://img.shields.io/badge/Installer-Windows-32A832)](https://github.com/Alban1911/Rose/releases/latest) [![Ko-Fi](https://img.shields.io/badge/KoFi-Donate-C03030?logo=ko-fi&logoColor=white)](https://ko-fi.com/roseapp) [![Discord](https://img.shields.io/discord/1490473857075642621?color=32A832&logo=discord&logoColor=white&label=Discord)](https://discord.com/invite/roseskins) [![License](https://img.shields.io/badge/License-MIT-C03030)](LICENSE) [![Downloads](https://img.shields.io/github/downloads/Alban1911/Rose/total?color=32A832&label=Downloads&cacheSeconds=86400)](https://github.com/Alban1911/Rose/releases/latest)


</div>

---

## Overview

Lust is an open-source automatic skin changer for League of Legends that enables seamless access to all skins in the game. The application runs silently in the system tray and automatically detects skin selections during champion select, injecting the chosen skin when the game loads.

Built on the [Pengu Loader](https://github.com/PenguLoader/PenguLoader) framework, Lust integrates JavaScript extensions into the League Client to enable modular UI interactions. It strictly modifies local rendering variables to display custom models and textures. It is designed purely as an exploration of client-side asset management, providing no manipulation of network data, memory states, or gameplay mechanics, thereby **offering zero competitive advantage**.

## Architecture

Lust consists of three main components:

### Python Backend

- **LCU API Integration**: Communicates with the League Client via the League Client Update (LCU) API
- **Skin Injection**: Handles skin injection compatible with Riot Vanguard
- **WebSocket Bridge**: Operates a WebSocket server for real-time communication with frontend plugins
- **Skin Management**: Downloads and manages skin files from the [LeagueSkins repository](https://github.com/Alban1911/LeagueSkins)
- **Party Mode**: Enables skin sharing between friends in the same lobby via a Cloudflare WebSocket relay
- **Game Monitoring**: Tracks game state, champion select phases, and loadout countdowns
- **Auto-Updater**: Checks GitHub for new releases and prompts users to install updates
- **Analytics**: Sends a startup ping, a 15-minute presence heartbeat, and a best-effort close ping (configurable, runs in a background thread)

### Analytics and privacy

Lust sends a pseudonymous, randomly generated installation ID and the app version
to `https://analytics.rosekeys.site/` when analytics are enabled. The ID is not derived
from the Windows Machine GUID. Analytics can be disabled with
`ANALYTICS_ENABLED = False` in `config.py`.

The analytics API and dashboard are maintained separately from this public
client repository. Only aggregate usage metrics are exposed through the
dashboard; raw activity and server credentials remain private.

### Cloudflare Workers

- **lust-party-relay**: Durable Object-backed WebSocket relay that manages party rooms (max 10 members per room) for real-time skin selection broadcasting between friends. It refuses Lust versions older than 1.4.4

### Pengu Loader Plugins

Lust includes a suite of JavaScript plugins that extend the League Client UI:

- **LUST-UI**: Unlocks locked skin previews in champion select, enabling hover interactions on all skins
- **LUST-SkinMonitor**: Monitors currently selected skin's name and sends it to the Python backend via WebSocket. It also hosts the bridge the other plugins use to talk to Lust
- **LUST-CustomSkinSelector**: Lists the custom skin mods made for the hovered skin and applies the one you pick
- **LUST-CustomWheel**: Custom mods panel for maps, fonts, announcers and other mods
- **LUST-ChromaWheel**: Enhanced chroma selection interface for choosing any chroma variant
- **LUST-FormsWheel**: Custom form selection interface for skins with multiple forms (Elementalist Lux, Sahn Uzal Mordekaiser, Spirit Blossom Morgana, Radiant Sett)
- **LUST-SettingsPanel**: Settings panel accessible from the League of Legends Client
- **LUST-RandomSkin**: Random skin selection feature
- **LUST-HistoricMode**: Access to the last used skin for every champion
- **LUST-PartyMode**: Party mode UI — displays a panel in lobby and champion select to enable skin sharing, view connected peers, and see friends' skin selections in real time
- **LUST-I18n**: Translates Lust's menus into the language picked in Settings, else the League client's
- **LUST-Jade**: Client customization — regalia borders, backgrounds, banners, icons, titles, and win/loss stats (shipped disabled)

## How It Works

1. **League Client Integration**: Lust activates **[Pengu Loader](https://github.com/PenguLoader/PenguLoader)** on startup, which injects the JavaScript plugins into the League Client. If the client is already open, Lust restarts it so the plugins load (during champion select, the restart waits for the lobby or the end of the game)
2. **Skin Detection**: When you hover over a skin in champion select, `LUST-SkinMonitor` detects the selection and sends it to the Python backend
3. **Game Opening Delay**: To give the injection time to happen, Lust suspends the game process until the overlay is ready. If Lust closes during that window, it resumes the game the next time it starts
4. **Game Injection**: Lust injects the selected skin when the game starts
5. **Seamless Experience**: The skin loads as if you owned it, with full chroma support and no gameplay impact (Lust will **never** provide any competitive advantage to its users)

## Features

- **Smart Injection**: Never injects skins you already own
- **Custom Mods**: Custom skins, maps, fonts and announcers (`.fantome`, `.zip` and `.modpkg`)
- **Party Mode**: Friends running Lust 1.4.4 or newer see each other's skins and custom mods in game
- **Loading Screen Name**: The loading screen shows the injected skin's name; the chat and the name over your champion keep the champion's
- **Multi-Language Support**: Works with any client language, with Lust's menus in 22 languages
- **Open Source**: Fully open source and extensible
- **Free**: If you bought this software, you got scammed 💀

## Requirements

- **Windows 10/11**
- **League of Legends** installed
- **LTK patcher** - You must provide it yourself (see below)

### LTK Patcher Requirement

Due to DMCA restrictions, Lust cannot distribute the LTK patcher. Get its two files, `ltk_patcher_host.exe` and `ltk_patcher_dll.dll`, from an LTK Manager install.

On first launch, Lust asks for these files and opens its tools folder, where they go. The patcher stops working with game builds released after its end-of-life date: Lust then tells you to update LTK Manager and replace both files.

## Installation

1. Download the latest installer from [Releases](https://github.com/Alban1911/Rose/releases/latest)
2. Run the installer as Administrator
3. Launch Lust from the Start Menu or desktop shortcut

## Building from source

Lust builds the Pengu Loader executable from the vendored source in
`vendor/PenguLoader-1.1.6/` as part of the normal Lust build. You do not need
to download or commit a prebuilt `Pengu Loader.exe`.

### Prerequisites

- Windows 10/11
- Python 3.11 or newer
- Visual Studio Build Tools with the .NET desktop build tools, WPF support,
  and the .NET Framework 4.7.2 targeting pack (for Pengu Loader), and the
  MSVC C++ build tools (for Lust's stand-in `cslol-dll.dll`)
- Inno Setup 6 if you also want to create the installer

Clone the repository and enter its directory:

```powershell
git clone https://github.com/Alban1911/Rose.git
cd Lust
```

Install the Python dependencies first:

```powershell
python -m pip install -r requirements.txt
```

Build the loader by itself, if needed:

```powershell
python scripts/build_pengu_loader.py
```

Build Lust (rebuilds the loader and the `cslol-dll.dll` stand-in):

```powershell
python scripts/build_pyinstaller.py
```

The packaged application is written to `dist/Lust/`. To build both Lust and
the Windows installer in one step:

```powershell
python scripts/build_all.py
```

The installer is written to `installer/Lust_Setup_<version>.exe`. Use
`scripts/build_pyinstaller.py` or `scripts/build_all.py` instead of invoking
`pyinstaller Lust.spec` directly, because the Lust build scripts compile
Pengu Loader first.

To create the update package the auto-updater downloads from a release
(`installer/update_package_<version>.zip`, `hashes.game.txt` excluded):

```powershell
python scripts/create_update_package.py
```

## Credits

Lust uses the [official Pengu Loader](https://github.com/PenguLoader/PenguLoader)
project. Its source is vendored and built as part of Lust, with Lust-specific
lifecycle integration added around the loader. Please see the
[official Pengu Loader license](https://github.com/PenguLoader/PenguLoader/blob/main/LICENSE)
and credit the Pengu Loader contributors.

## Contributing

Contributions are welcome. Report bugs and suggest features through the
[issue forms](https://github.com/Alban1911/Rose/issues/new/choose), and ask
for installation help on [Discord](https://discord.com/invite/roseskins).

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, the tests and
checks that CI runs on every pull request, and the project structure.

## Legal Disclaimer

This project is not endorsed by or affiliated with Riot Games. Riot Games and all related properties are trademarks or registered trademarks of Riot Games, Inc.

Riot Games does not allow custom skins that reproduce its real skins, which is what Lust does. Use Lust at your own risk: its developers are not responsible for any consequence of using it, including account suspensions or bans.

## Support

If you enjoy Lust and want to support its development:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/roseapp)

Your support helps keep the project alive and motivates continued development!

---

**Lust** - _League, unlocked._
