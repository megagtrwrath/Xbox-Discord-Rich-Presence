# Xbox Discord Rich Presence

The first Discord Rich Presence system designed specifically for the original Xbox.

**ShortcutRelayXBE** is a simple launcher for the original Xbox.

You tell it what game or app to launch by editing a small config file, and it sends that game's TitleID to a Discord relay so your status can update.

No menus. No dashboard. Just launch and go.

**ShortcutRelayPy** is a Python script for **XBMC** that does the same thing, but with a spiffy dashboard wrapper.

---

## How It Works (XBE)

- Reads the path to your game or app from a file called `shortcut.ini`
- Launches the specified `.xbe` file (OFFICIAL Games currently, homebrew is iffy!)
- Sends the game’s TitleID to a Discord relay over your local network
- Automatically mounts all drives (F, G, etc.) before launching

---

## Setup (XBE)

1. Put `ShortcutRelayXBE.xbe` on your Xbox
2. In the same folder, create a file named `shortcut.ini`
3. There are 3 listening modes in xbdStats-go, Websockets (Port 1101), UDP (Port 1102), TCP (Port 1103)
4. If you plan on compiling yourself, use Debug, not Release.
5. Add this to the file:

```
[Shortcut]
Path=F:\Games\Halo 2\default.xbe
RelayIP=192.168.0.174
RelayPort=1102
```

- `Path`: Where the game or app is located on your Xbox
- `RelayIP`: IP address of the PC running the Discord bot
- `RelayPort`: The port your bot is listening on

## Setup (XBMC Python Script)
1. Download `default.py` and `default.tbn` 
2. Modify `SERVER_IP` to point at the machine running `xbdStats` (optionally, modify "DEFAULT_PATH" to the path of your choosing if you'd like to point the file browser at your primary game directory instead of individual drives).
3. Copy your modified `default.py` to `Q:/scripts/ShortcutRelayPy`
2. In `XBMC`, select `Scripts`, then `ShortcutRelayPy`.
3. Select the game you'd like to launch, and you're done!

## Server

1. [xbdStats](https://github.com/MobCat/xbdStats) python server.py is currently the fully tested version and has two listening modes. Websockets (Port 1101), and UDP (Port 1102).
2. xbdStats-go has 3 listening modes Websockets (Port 1101), UDP (Port 1102), TCP (Port 1103).
3. The Windows binary gets flagged as a trojan due to hueristics (Its not signed, and the source is available. Run it raw if you'd like, nothing sketchy.)
4. xbdStats-go's macOS build doesn't like UDP.
5. Linux is currently untested. Please report any bugs on the [Xbox-Scene Discord](https://discord.gg/xbox-scene) in the TeamUIX channel.
---

## Discord Integration

This launcher works with [xbdStats](https://github.com/MobCat/xbdStats) — a small Python based Discord Presence applet made by **MobCat**.
When you use the shortcut (either the XBE or Python script), the server receives a message and updates your Discord presence to show what you're playing, just like on modern consoles.

---

## Why Use This?

- No extra menus or frontends required.
- Perfect for shortcut entries on a dashboard or file browser.
- Lets your friends see what you're playing.
- Simple and fast.

---

## Credits

- **CrunchBite** - base launcher logic and device mounting used from [packed-xbe-launcer](https://github.com/CrunchBite/packed-xbe-launcher)
- **MobCat** - `xbdStats` Discord Relay and API, and xbeParse logic.
- **Milenko** - `xbeParse`, ini support, relay integration, cleanup.
- **Team Resurgent** - Networking logic and xboxinternals.h from [PrometheOS](https://github.com/Team-Resurgent/PrometheOS-Firmware)
- **faithvoid** - `XBMC` script integration and development.

---
