# ShortcutRelayXBE

**ShortcutRelayXBE** is a simple launcher for the original Xbox.

You tell it what game or app to launch by editing a small config file, and it sends that game's TitleID to a Discord relay so your status can update.

No menus. No dashboard. Just launch and go.

---

## How It Works

- Reads the path to your game or app from a file called `shortcut.ini`
- Launches the specified `.xbe` file (OFFICIAL Games currently, homebrew is iffy!)
- Sends the game’s TitleID to a Discord relay over your local network
- Automatically mounts all drives (F, G, etc.) before launching

---

## Setup

1. Put `ShortcutRelayXBE.xbe` on your Xbox
2. In the same folder, create a file named `shortcut.ini`
3. Add this to the file:


- `Path`: Where the game or app is located on your Xbox
- `RelayIP`: IP address of the PC running the Discord bot
- `RelayPort`: The port your bot is listening on

## Example INI
```
[Shortcut]
Path=F:\Games\Halo 2\default.xbe
RelayIP=192.168.0.174
RelayPort=1102
```
---

## Discord Integration

This launcher works with [xbdStats](https://github.com/MobCat/xbdStats) — a small Python based Discord Presence applet made by **MobCat**.

When you use this shortcut, the server receives a message and updates your Discord presence to show what you’re playing, just like on modern consoles.

---

## Why Use This?

- No extra menus or frontends
- Perfect for shortcut entries on a dashboard or file browser
- Lets your friends see what you're playing
- Simple and fast

---

## Credits

- **CrunchBite** – base launcher logic and device mounting used from [packed-xbe-launcer](https://github.com/CrunchBite/packed-xbe-launcher)
- **mobcat** – xbdStats Discord Relay and API, and xbeParse logic.
- **Milenko** – `xbeParse`, ini support, relay integration, cleanup.
- **Team Resurgent** - Networking logic and xboxinternals.h from [PrometheOS](https://github.com/Team-Resurgent/PrometheOS-Firmware)

---
