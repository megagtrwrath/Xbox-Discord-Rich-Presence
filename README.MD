# Xbox Discord Rich Presence

The first Discord Rich Presence system designed specifically for Xbox and Xbox 360 Consoles

**ShortcutRelayXBE** is a simple launcher for the original Xbox.

You tell it what game or app to launch by editing a small config file, and it sends that game's TitleID to a Discord relay so your status can update.

**ShortcutRelayPy** is a Python script for **XBMC** that does the same thing, but with a spiffy dashboard wrapper.

**xbdStats-go** is the Discord awareness `server` that runs on your PC. It's what tells Discord what you're playing.

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
2. Modify `SERVER_IP` to point at the machine running `xbdStats` (optionally, modify `DEFAULT_PATH` to the path of your choosing if you'd like to point the file browser at your primary game directory instead of individual drives).
3. Copy your modified `default.py` to `Q:/scripts/ShortcutRelayPy`
4. In `XBMC`, select `Scripts`, then `ShortcutRelayPy`.
5. Select the game you'd like to launch, and you're done!
6. (Optional) If you'd like to automatically clear your Discord Presence upon startup, copy 'clearpresence.py' to `Q:/scripts/ShortcutRelayPy`, and add `xbmc.executebuiltin("XBMC.RunScript(Q:/scripts/ShortcutRelayPy/clearpresence.py)")` to `autoexec.py` in `Q:/scripts` (create the file if it's not available by default). You can modify the behaviour of this script (ie; showing your current dashboard) by changing `TITLE_ID` in `clearpresence.py` to the title ID of your choosing.

## Setup (XBMC "Media Edition" Script - Experimental!)
1. Download `ShortcutRelay.py`, `MediaPresence.py` and `xbdStats-media.py` from the "XBMC/MediaServer" section of the repository
2. Copy `ShortcutRelay.py` to `Q:/scripts/ShortcutRelay/default.py`
3. Copy `MediaPresence.py` to `Q:/scripts/MediaPresence/default.py`
4. Run the modified "xbdStats-media.py" file on your host machine (this will **NOT** work with Milenko or MobCat's version!), and modify it with a text editor to add your own TMDB/TVDB API keys. (this may change in the future, need to double-check individual API rules).
5. In `XBMC`, select `Scripts`, then `ShortcutRelay` if you want to launch a game, or `MediaPresence` if you want to run a background listening script that reports your current media to xbdStats-media. (a **128MB Xbox** is recommended for MediaPresence due to RAM issues with larger video files, but smaller files should work fine for 64MB systems!)
6. ???
7. Profit!
8. (Optional) If you'd like to automatically launch Media Presence upon startup, add `xbmc.executebuiltin("XBMC.RunScript(Q:/scripts/MediaPresence/default.py)")` to `autoexec.py` in `Q:/scripts` (create the file if it's not available by default).
(Please note that this version of the xbdStats server does NOT support the Xbox 360 at all, this is solely for the original Xbox until further notice).
9. (Optional) If you'd like to seamlessly launch games from the Games menu in XBMC, add the following to the end of Q:/system/keymaps/gamepad.xml (this will set "Black" / "RB to launch your game and send presence automatically, but any free button can be mapped instead)
```
  <Window1>
    <gamepad>
      <black>RunScript(Q:\skin\Cortana-X\scripts\chat\relay.py)</black>
    </gamepad>
  </Window1>
```

## Server

1. [xbdStats](https://github.com/MobCat/xbdStats) python server.py is currently the fully tested version and has two listening modes. Websockets (Port 1101), and UDP (Port 1102).
2. xbdStats-go has 3 listening modes Websockets (Port 1101), UDP (Port 1102), TCP (Port 1103) and `Xbox 360` support through utilizing the JRPC plugin family.
3. The Windows binary gets flagged as a trojan due to hueristics (Its not signed, and the source is available. Run it raw if you'd like, nothing sketchy.)
4. xbdStats-go's macOS build doesn't like UDP.
5. Linux is currently untested. Please report any bugs on the [Xbox-Scene Discord](https://discord.gg/xbox-scene) in the TeamUIX channel.

## Server (Xbox 360 Support)
1. You must be using `xbdStats-go` and have a modded console running `dashlaunch` and `JRPC`.
2. Configure the `xbdStats.ini` and make sure you download the `xbox360.json` place those in the same folder as your binary.
```
[Xbox360]
IP=192.168.0.162 // Your consoles IP.
PollInterval=30  // How often you want it to poll, 30 seconds seems fair.
Verbose=0 // Extra logs, not really needed for regular use.
Enabled=True // Enabled can be true or false. We dont want to hammer a non-existent console.
```
## Server (XBMC TMDB Support) (BETA/In-Development)
1. You need to use a `TMDB` API key, you can get one from [TMDB](https://www.themoviedb.org/settings/api). Set it in the `xbdStats.ini` file under the `[media]` section.
2. This feature is just a playful demo right now, it only works on `TCP`, the Demo Payload below will show you as watching Ghostbusters on Discord.
```
{"id":"tt0087332","media":true}
```
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
- **Emma(IPG)** - For discussing XBDM support this quit convo sent Milenko down a rabbithole.
- **Scotch** - Research, development & testing on XBMC 4.0.
- **TheTVDB**, **The Movie Database** & **MusicBrainz** - For the free API functionality!
---
