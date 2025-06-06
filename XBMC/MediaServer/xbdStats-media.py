# xbdStats - Media Centre Edition - fork by faithvoid (2025)
#!/env/Python3.10.4
#/MobCat (2024)

import asyncio
import websockets, socket, time, urllib.request, json, requests
import threading
from discordrp import Presence
from websockets.legacy.server import WebSocketServerProtocol as wetSocks
import re

# Discord API Client ID
clientID = "1304454011503513600"
presence = Presence(clientID)

# API / CDN / Image URLs
APIURL = "https://mobcat.zip/XboxIDs"
CDNURL = "https://raw.githubusercontent.com/MobCat/MobCats-original-xbox-game-list/main/icon"
MUSIC_LARGE = "https://cdn.discordapp.com/app-assets/1379734520508579960/1380359849233092659.png"
MUSIC_SMALL = "https://cdn.discordapp.com/app-assets/1379734520508579960/1379736461946916874.png"

# API Keys
TMDB_API_KEY = "YOURAPIKEYHERE" # Required for TMDB usage!
TVDB_API_KEY = "YOURAPIKEYHERE" # Required for TVDB usage!
_tvdb_jwt = None
_tvdb_jwt_time = 0

# Broadcast "XBDSTATS_ONLINE" for auto-discovery
def broadcast_online(port=1102, interval=3):
    bc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    bc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    msg = b"XBDSTATS_ONLINE"
    while True:
        try:
            bc_sock.sendto(msg, ('<broadcast>', port))
        except Exception as e:
            print("[Broadcast] Error:", e)
        time.sleep(interval)

# Get token from TVDB
def get_tvdb_jwt():
    global _tvdb_jwt, _tvdb_jwt_time
    import time
    if _tvdb_jwt and (time.time() - _tvdb_jwt_time) < 14400:
        return _tvdb_jwt
    url = 'https://api4.thetvdb.com/v4/login'
    data = json.dumps({"apikey": TVDB_API_KEY}).encode("utf-8")
    resp = requests.post(url, data=data, headers={'Content-Type': 'application/json'}, timeout=5)
    resp.raise_for_status()
    _tvdb_jwt = resp.json()['data']['token']
    _tvdb_jwt_time = time.time()
    return _tvdb_jwt

# Splits artist title information for MusicBrainz usage
def split_artist_title(idstr):
    # Accepts "Artist - Title" and splits it
    parts = idstr.split(' - ', 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return None, None

# Fetch various information (ie; cover art) for music files via MusicBrainz  
def fetch_musicbrainz_info(artist, title):
    try:
        # Search recording by artist and title
        query = f'artist:"{artist}" AND recording:"{title}"'
        url = f'https://musicbrainz.org/ws/2/recording/?query={urllib.parse.quote(query)}&fmt=json&limit=1'
        headers = {'User-Agent': 'xbdStats/1.0 ( faithvoid@github )'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        results = resp.json().get('recordings', [])
        if not results:
            return None, None, None

        rec = results[0]
        track_title = rec.get('title', title)
        artist_name = rec['artist-credit'][0]['name'] if rec.get('artist-credit') else artist
        release_list = rec.get('releases', [])
        release_mbid = release_list[0]['id'] if release_list else None

        cover_url = None
        if release_mbid:
            # Fetch the JSON listing of available cover art
            caa_url = f'https://coverartarchive.org/release/{release_mbid}/'
            caa_resp = requests.get(caa_url, headers={'Accept': 'application/json'}, timeout=10)
            if caa_resp.status_code == 200:
                caa_json = caa_resp.json()
                images = caa_json.get('images', [])
                # Look for the front cover image, prefer 500px thumbnail if available
                for img in images:
                    if img.get('front', False):
                        cover_url = img.get('thumbnails', {}).get('500', img.get('image'))
                        break
                if not cover_url and images:
                    # fallback to first image if no explicit 'front'
                    cover_url = images[0].get('thumbnails', {}).get('500', images[0].get('image'))
        return track_title, artist_name, cover_url
    except Exception as e:
        print(f"[MusicBrainz ERROR] {e}")
        return None, None, None

# Retrieve TVDB information for TV shows (requires API key!)
def fetch_tvdb(item_type, item_id):
    try:
        jwt = get_tvdb_jwt()
        if item_type == "series":
            url = f"https://api4.thetvdb.com/v4/series/{item_id}"
        elif item_type == "episode":
            url = f"https://api4.thetvdb.com/v4/episodes/{item_id}"
        else:
            raise ValueError("item_type must be 'series' or 'episode'")
        headers = {"Authorization": f"Bearer {jwt}"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code != 200:
            return None
        data = resp.json().get('data', {})

        if item_type == "series":
            title = data.get('name', 'Unknown Series')
            overview = data.get('overview', '')
            poster_url = ''
            for art in data.get('artworks', []):
                if art.get('type') == 'poster':
                    poster_url = art.get('image')
                    break
            return title, overview, poster_url, item_id

        elif item_type == "episode":
            ep_title = data.get('name', '') or 'Unknown Episode'
            overview = data.get('overview', '')
            aired_season = data.get('seasonNumber', None)
            aired_episode = data.get('number', None)
            series_id = data.get('seriesId', None)
            series_name = ''
            poster_url = data.get('image', '')
            # Optionally fetch series info for name/poster if needed
            if series_id:
                series_info = fetch_tvdb("series", str(series_id))
                if series_info:
                    series_name = series_info[0]
                    if not poster_url:
                        poster_url = series_info[2]
            return ep_title, overview, poster_url, aired_season, aired_episode, series_name, series_id

    except Exception as e:
        print("[TVDB ERROR] %s" % e)
        return None

# Check if received input is TVDB Episode ID or not 
def is_tvdb_episode_id(idstr):
    return idstr.isdigit() and 0 < int(idstr) < 99999999

# Fetch IMDB information via TMDB (requires API key!)
def fetch_tmdb_by_imdb(imdb_id):
    url = f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={TMDB_API_KEY}&external_source=imdb_id"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return None
        data = resp.json()
        results = data.get("movie_results", [])
        if not results:
            return None
        tmdb = results[0]
        title = tmdb.get("title", "Unknown Title")
        overview = tmdb.get("overview", "")
        poster_path = tmdb.get("poster_path", "")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        tmdb_id = tmdb.get("id", "")
        return title, overview, poster_url, tmdb_id
    except Exception as e:
        print(f"[TMDB ERROR] {e}")
        return None

# Clusterfuck of code ahoy! tl;dr this builds presence information depending on whether the information received is music, television, movies, or games.
def build_presence(dataIn):
    is_media = dataIn.get("media", False)
    is_music = dataIn.get("music", False)
    xbmc_state = "Now Listening - XBMC" if is_music else "Now Playing - XBMC"
    idstr = dataIn.get("id", "")
    presenceData = {}
    buttons = []
    log_string = ""

    # Weird fix for music presence issues. Music function takes priority above all else, if the received media isn't music, it defaults to TVDB/TMDB instead.
    if is_music:
        artist, track = split_artist_title(idstr)
        mb_title, mb_artist, mb_cover = None, None, None
        if artist and track:
            mb_title, mb_artist, mb_cover = fetch_musicbrainz_info(artist, track)
        TitleName = f"{mb_artist} - {mb_title}" if mb_title and mb_artist else idstr
        presenceData = {
            "type": 0,
            "details": TitleName,
            "state": "Now Listening - XBMC",
            "timestamps": {"start": int(time.time())},
            "assets": {
                "large_image": mb_cover if mb_cover else MUSIC_LARGE,
                "large_text": TitleName,
            },
            "instance": True,
        }
        log_string = f"Now Listening {idstr} - {TitleName}"
    elif is_valid_imdb_id(idstr):
        tmdb = fetch_tmdb_by_imdb(idstr)
        if tmdb:
            title, overview, poster_url, tmdb_id = tmdb
            if overview and overview.strip():
                large_text = overview[:125] + "..." if len(overview) > 128 else overview
            else:
                large_text = "Media info not found."
            presenceData = {
                "type": 0,
                "details": title,
                "state": xbmc_state,
                "timestamps": {"start": int(time.time())},
                "assets": {
                    "large_image": poster_url if poster_url else "xbmc",
                    "large_text": large_text,
                    "small_image": "https://raw.githubusercontent.com/MobCat/MobCats-original-xbox-game-list/main/icon/0999/09999990.png",
                },
                "instance": True,
                "buttons": [{"label": "View on IMDb", "url": f"https://www.imdb.com/title/{idstr}"}],
            }
            log_string = f"Now Playing {idstr} - {title}"
        else:
            fallback_title = fallback_title_from_filename(idstr) if is_filename(idstr) else idstr
            presenceData = {
                "type": 0,
                "details": fallback_title,
                "state": "Unlisted content",
                "timestamps": {"start": int(time.time())},
                "assets": {
                    "large_image": "xbmc",
                    "large_text": "Media info not found.",
                    "small_image": "https://raw.githubusercontent.com/MobCat/MobCats-original-xbox-game-list/main/icon/0999/09999990.png",
                },
                "instance": True,
            }
            log_string = f"Now Playing {idstr} - {fallback_title}"
    elif is_tvdb_episode_id(idstr):
        tvdb_ep = fetch_tvdb("episode", idstr)
        if tvdb_ep:
            ep_title, overview, poster_url, aired_season, aired_episode, series_name, series_id = tvdb_ep
            if overview and overview.strip():
                large_text = overview[:125] + "..." if len(overview) > 128 else overview
            else:
                large_text = "Media info not found."
            season_str = f"{int(aired_season):02d}" if aired_season is not None else "??"
            episode_str = f"{int(aired_episode):02d}" if aired_episode is not None else "??"
            details_text = f"{series_name}: {ep_title} (S{season_str}E{episode_str})"
            presenceData = {
                "type": 0,
                "details": details_text,
                "state": xbmc_state,
                "timestamps": {"start": int(time.time())},
                "assets": {
                    "large_image": poster_url if poster_url else "xbmc",
                    "large_text": large_text,
                    "small_image": "https://raw.githubusercontent.com/MobCat/MobCats-original-xbox-game-list/main/icon/0999/09999990.png",
                },
                "instance": True,
                "buttons": [{"label": "View on TVDB", "url": f"https://www.thetvdb.com/series/{series_id}/episodes/{idstr}"}],
            }
            log_string = f"Now Playing {idstr} - {details_text}"
        else:
            fallback_title = fallback_title_from_filename(idstr) if is_filename(idstr) else idstr
            presenceData = {
                "type": 0,
                "details": fallback_title,
                "state": "Unlisted content",
                "timestamps": {"start": int(time.time())},
                "assets": {
                    "large_image": "xbmc",
                    "large_text": "Media info not found.",
                    "small_image": "https://raw.githubusercontent.com/MobCat/MobCats-original-xbox-game-list/main/icon/0999/09999990.png",
                },
                "instance": True,
            }
            log_string = f"Now Playing {idstr} - {fallback_title}"
    elif is_media or is_music:  # Fallback for media/music with no match above
        fallback_title = fallback_title_from_filename(idstr) if is_filename(idstr) else idstr
        xbmc_state = "Now Listening - XBMC" if is_music else "Now Playing - XBMC"
        presenceData = {
            "type": 0,
            "details": fallback_title,
            "state": xbmc_state,
            "timestamps": {"start": int(time.time())},
            "assets": {
                "large_image": "xbmc",
                "large_text": "Media info not found.",
                "small_image": "https://raw.githubusercontent.com/MobCat/MobCats-original-xbox-game-list/main/icon/0999/09999990.png",
            },
            "instance": True,
        }
        log_string = f"{xbmc_state} {idstr} - {fallback_title}"
    else:  # Fallback for games
        XMID, TitleName = lookupID(dataIn['id'])
        inTitleID = dataIn['id'].upper()
        presenceData = {
            "type": 0,
            "details": TitleName,
            "timestamps": {"start": int(time.time())},
            "assets": {
                "large_image": f"{CDNURL}/{inTitleID[:4]}/{inTitleID}.png",
                "large_text": f"TitleID: {dataIn['id']}",
                "small_image": "https://cdn.discordapp.com/avatars/1304454011503513600/6be191f921ebffb2f9a52c1b6fc26dfa",
            },
            "instance": True,
        }
        if XMID != "00000000":
            presenceData["buttons"] = [{"label": "Title Info", "url": f"{APIURL}/title.php?{XMID}"}]
        elif 'name' in dataIn and dataIn['name']:
            presenceData['details'] = dataIn['name']
        log_string = f"Now Playing {dataIn['id']} - {TitleName}"
    return presenceData, log_string

# Check if the received information is a filename or not - probably needs work
def is_filename(idstr):
    idstr = idstr.lower()
    return idstr.endswith('.mkv') or idstr.endswith('.mp4') or idstr.endswith('.avi')

# Generate fallback video title from filename.
def fallback_title_from_filename(filename):
    import os, re
    name = os.path.splitext(os.path.basename(filename))[0]
    name = re.sub(r'[._-]+', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip().title()

# Check if received input is IMDB ID or not 
def is_valid_imdb_id(imdb_id):
    return bool(re.fullmatch(r"tt\d{7,}", imdb_id))

# Get local IP address
def getIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return '.'.join(IP.split('.'))

# Look up Xbox Title IDs via MobCat's API
def lookupID(titleID):
    try:
        with urllib.request.urlopen(f"{APIURL}/api.php?id={titleID}") as url:
            apiData = json.load(url)
            if 'error' not in apiData:
                XMID = apiData[0]['XMID']
                TitleName = apiData[0]['Full_Name']
            else:
                XMID = '00000000'
                TitleName = 'Unknown Title'
    except Exception as e:
        print(e)
        XMID = '00000000'
        TitleName = 'Unknown Title'
    return XMID, TitleName

# Clusterfuck of uncommented code ahoy!
async def clientHandler(websocket: wetSocks):
    try:
        print(f"{int(time.time())} {websocket.remote_address} Xbox connected!")
        async for message in websocket:
            print(f"{int(time.time())} {websocket.remote_address} {message}")
            if message == "" or message == "{}":
                print(f"{int(time.time())} {websocket.remote_address} Clear Presence signal received.")
                presence.clear()
                continue
            dataIn = json.loads(message)
            if not dataIn.get("id"):
                print(f"[WebSocket] Clear signal received from {websocket.remote_address}, clearing presence.")
                presence.clear()
                continue
            presenceData, log_string = build_presence(dataIn)
            presence.set(presenceData)
            print(f"[WebSocket] {log_string}")
    except websockets.ConnectionClosedOK:
        print(f"{int(time.time())} {websocket.remote_address} Client disconnected normally")
    except websockets.ConnectionClosedError as e:
        print(f"{int(time.time())} {websocket.remote_address} Client disconnected with error: {e}")
    finally:
        if websocket.closed:
            print(f"{int(time.time())} {websocket.remote_address} Connection closed. Presence cleared.")
            presence.clear()

# UDP Listener
def listen_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 1102))  # Same port as WebSocket
    print("[UDP] Listening for raw relay packets on port 1102...")

    while True:
        data, addr = sock.recvfrom(1024)
        try:
            message = data.decode("utf-8").strip()
            if message == "XBDSTATS_ONLINE":
                continue
            print(f"[UDP] From {addr}: {message}")
            dataIn = json.loads(message)
            if not dataIn.get("id"):
                print(f"[UDP] Clear signal received from {addr}, clearing presence.")
                presence.clear()
                continue
            presenceData, log_string = build_presence(dataIn)
            presence.set(presenceData)
            print(f"[UDP] {log_string}")
        except Exception as e:
            print(f"[UDP ERROR] {e}")

# TCP Listener
def listen_tcp():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', 1103))
    server_sock.listen(5)
    print("[TCP] Listening for raw relay packets on port 1103...")

    while True:
        try:
            conn, addr = server_sock.accept()
            threading.Thread(target=handle_tcp_client, args=(conn, addr), daemon=True).start()
        except Exception as e:
            print(f"[TCP ERROR] Accept error: {e}")

def handle_tcp_client(conn, addr):
    print(f"[TCP] Connection from {addr}")
    buffer = ""
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    print(f"[TCP] From {addr}: {line}")
                    dataIn = json.loads(line)
                    if not dataIn.get("id"):
                        print(f"[TCP] Clear signal received from {addr}, clearing presence.")
                        presence.clear()
                        continue
                    presenceData, log_string = build_presence(dataIn)
                    presence.set(presenceData)
                    print(f"[TCP] {log_string}")
                except Exception as e:
                    print(f"[TCP ERROR] {e}")
    except Exception as e:
        print(f"[TCP ERROR] Connection error from {addr}: {e}")
    finally:
        conn.close()
        print(f"[TCP] Connection closed from {addr}")

# Main async WebSocket server entry point
async def main():
    serverIP = getIP()
    server = await websockets.serve(clientHandler, serverIP, 1102)
    print(f"Server started on ws://{serverIP}:1102\nWaiting for connection...")

    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        presence.close()
        server.close()
        await server.wait_closed()
        print("Server closed")
        exit()

# Banner + launch
print(r'''
      _         _ __ _         _       
__  _| |__   __| / _\ |_  __ _| |_ ___ 
\ \/ / '_ \ / _` \ \| __|/ _` | __/ __|
 >  <| |_) | (_| |\ \ |_  (_| | |_\__ \\
/_/\_\_.__/ \__,_\__/\__|\__,_|\__|___/
xbStats Server 20241111
''')

threading.Thread(target=broadcast_online, daemon=True).start()
threading.Thread(target=listen_udp, daemon=True).start()
threading.Thread(target=listen_tcp, daemon=True).start()

asyncio.run(main())
